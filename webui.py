# -*- coding: UTF-8 -*-
#!/usr/bin/env python

import atexit
from copy import deepcopy
import datetime
import json
import logging
from logging.handlers import RotatingFileHandler
from os import environ, path, walk
from pprint import pprint
from time import strftime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.base import ConflictingIdError, JobLookupError
from apscheduler.triggers.interval import IntervalTrigger
from flask import Flask, flash, redirect, render_template, request
from flask_sqlalchemy import SQLAlchemy
from redis import Redis

from config import DEBUG, FLASK_SECRET_KEY, IPP, SETTINGS_FILE, SCRIPT_ROOT, SPIDERS, WEBUI_DATABASE_URI, REDIS_HOST, REDIS_PORT, \
    __version__, WEBUI_HOST, WEBUI_PORT, FEEDS_DIR, LOG_DIR, WEBUI_LOGGING
from application.misc import OK, SpiderStatus, Settings
from application.models import Jobs, PeriodicJobs, init_db
from tasks import run_job, run_periodic_job


BASE_DIR = path.abspath(path.dirname(__file__))
logger_level = logging.DEBUG if DEBUG else logging.ERROR
# print(logger_level)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Flask(
    __name__,
    static_folder=path.join(SCRIPT_ROOT, "webui", "static"),
    template_folder=path.join(SCRIPT_ROOT, "webui", "templates"),
)
app.secret_key = FLASK_SECRET_KEY
app.config["SCRIPT_ROOT"] = SCRIPT_ROOT
app.config["SQLALCHEMY_DATABASE_URI"] = WEBUI_DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["DATABASE_CONNECT_OPTIONS"] = {}

db = SQLAlchemy(app)

# Update db
if not path.exists(path.join(SCRIPT_ROOT, "data", "webui_2.db")):
    print("Rebuilding database ...")
    import sqlite3

    conn = sqlite3.connect(path.join(SCRIPT_ROOT, "data", "webui.db"))
    c = conn.cursor()
    # Backup
    c.execute("SELECT * FROM periodic_jobs")
    periodic_jobs = c.fetchall()
    c.execute("SELECT * FROM jobs")
    jobs = c.fetchall()
    # # Drop
    # c.execute("DROP TABLE IF EXISTS settings")
    # c.execute("DROP TABLE IF EXISTS periodic_jobs")
    # c.execute("DROP TABLE IF EXISTS jobs")
    conn.close()
    # Recreate
    init_db(WEBUI_DATABASE_URI)
    # Update
    for pj in periodic_jobs:
        print(pj)
        job = PeriodicJobs(
            spider_name=pj[3],
            scrape_type=pj[4],
            use_proxies=pj[5],
            file=pj[6],
            db=pj[7],
            images=pj[8],
            repeat_time=pj[9],
            enabled=pj[10],
        )
        db.session.add(job)
    db.session.commit()
    for j in jobs:
        print(j)
        job = Jobs(
            task_id=j[3],
            spider_name=j[4],
            spider_status=j[5],
            scrape_type=j[6],
            use_proxies=j[7],
            file=j[8],
            db=j[9],
            images=j[10],
            items_scraped=0,
            date_started=datetime.datetime.strptime(j[11], "%Y-%m-%d %H:%M:%S.%f"),
            date_finished=datetime.datetime.strptime(j[12], "%Y-%m-%d %H:%M:%S.%f"),
        )
        db.session.add(job)
    db.session.commit()
    print("Done.")

_redis = Redis(REDIS_HOST, REDIS_PORT)
version = '.'.join(map(str, __version__))
settings = Settings()
if path.isfile(SETTINGS_FILE):
    settings.load(SETTINGS_FILE)
else:
    settings.save(SETTINGS_FILE)
scheduler = None


def load_form_data(form, settings):
    params = {
        "delay": int(form.get("delay", settings.delay)),
        "timeout": int(form.get("timeout", settings.timeout)),
        "retries": int(form.get("retries", settings.retries)),
        "concurrent_requests": int(form.get("concurrent_requests", settings.concurrent_requests)),
        "scrape_type": int(form.get("scrape_type", settings.scrape_type)),
        "feed": 1 if request.form.get("feed", False) else settings.feed,
        "db": 1 if request.form.get("db", False) else settings.db,
        "images": 1 if request.form.get("images", False) else settings.images,
        "use_proxies": 1 if request.form.get("use_proxies", False) else settings.use_proxies,
        "mongo_uri": request.form.get("mongo_uri", settings.mongo_uri),
        "mongo_db": request.form.get("mongo_db", settings.mongo_db),
        "twitter_consumer_key": request.form.get("twitter_consumer_key", settings.twitter_consumer_key),
        "twitter_consumer_secret": request.form.get("twitter_consumer_secret", settings.twitter_consumer_secret),
        "twitter_access_token_key": request.form.get("twitter_access_token_key", settings.twitter_access_token_key),
        "twitter_access_token_secret": request.form.get("twitter_access_token_secret", settings.twitter_access_token_secret),
    }

    return params


def text_to_lines(text):
    lines = set()
    for line in text.strip().splitlines():
        lines.add(line.strip())

    return list(lines)


@app.before_first_request
def initialize():
    # Periodic Job init/update
    periodic_jobs = db.session.query(PeriodicJobs).all()
    current = dict()
    new = set()
    for job in periodic_jobs:
        current[job.spider_name] = job
    for spider in SPIDERS:
        new.add(spider[0])
    if not (set(current.keys()) == new):
        print("Updating periodic jobs table ...")
        # Delete all rows
        db.session.query(PeriodicJobs).delete()
        db.session.commit()
        # Insert
        for spider in SPIDERS:
            if spider[0] in current:
                pj = current[spider[0]]
                job = PeriodicJobs(
                    spider_name=pj.spider_name,
                    scrape_type=pj.scrape_type,
                    use_proxies=pj.use_proxies,
                    file=pj.file,
                    db=pj.db,
                    images=pj.images,
                    repeat_time=pj.repeat_time,
                    enabled=pj.enabled,
                )
            else:
                job = PeriodicJobs(
                    spider_name=spider[0],
                )
            db.session.add(job)
        db.session.commit()
    # Disable active jobs
    jobs = db.session.query(Jobs).filter(Jobs.spider_status < 2).all()
    for job in jobs:
        job.spider_status = 3
    db.session.commit()

    # Init scheduler
    global scheduler
    scheduler = BackgroundScheduler()
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())


@app.context_processor
def utility_processor():
    def timedelta(end_time, start_time):
        '''

        :param end_time:
        :param start_time:
        :param unit: s m h
        :return:
        '''
        if not end_time or not start_time:
            return ''
        if type(end_time) == str:
            end_time = datetime.datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
        if type(start_time) == str:
            start_time = datetime.datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
        total_seconds = (end_time - start_time).total_seconds()
        total_seconds = int(total_seconds)

        return readable_time(total_seconds)

    def readable_time(total_seconds):
        if not total_seconds:
            return '-'
        if total_seconds < 60:
            return '%s s' % total_seconds
        if total_seconds < 3600:
            return '%s m' % int(total_seconds / 60)

        return '%s h %s m' % (int(total_seconds / 3600), int((total_seconds % 3600) / 60))

    def str_date(date):
        return str(date).split('.')[0]

    return dict(timedelta=timedelta, readable_time=readable_time, str_date=str_date)


@app.context_processor
def ctx():
    return {
        "version": version,
        "debug": DEBUG,
    }


@app.teardown_request
def teardown_request(exception):
    if exception:
        db.session.rollback()
        db.session.remove()
    db.session.remove()


@app.route('/')
@app.route("/index")
def index():
    return redirect("/jobs/active")


@app.route("/jobs/active")
@app.route("/jobs/active/<int:job_id>")
def jobs_active(job_id=None):
    if job_id is not None:
        flash("Stopping the job id {}".format(job_id), "info")
        return redirect("/jobs/active")
    next_jobs = db.session.query(Jobs).filter(Jobs.spider_status == SpiderStatus.PENDING).all()
    running_jobs = db.session.query(Jobs).filter(Jobs.spider_status == SpiderStatus.RUNNING).all()

    return render_template(
        "jobs_active.html",
        next_jobs=next_jobs,
        running_jobs=running_jobs,
        now=datetime.datetime.now(),
    )


@app.route("/jobs/periodic")
def jobs_periodic():
    global settings
    disabled_jobs = db.session.query(PeriodicJobs).filter(PeriodicJobs.enabled == 0).all()
    enabled_jobs = db.session.query(PeriodicJobs).filter(PeriodicJobs.enabled == 1).all()

    twitter_usernames_file = path.join(BASE_DIR, "data", "twitter_usernames.txt")
    twitter_usernames = ''
    if path.isfile(twitter_usernames_file):
        with open(twitter_usernames_file, 'r') as f:
            twitter_usernames = f.read().strip()
    twitter_keywords_file = path.join(BASE_DIR, "data", "twitter_keywords.txt")
    twitter_keywords = ''
    if path.isfile(twitter_keywords_file):
        with open(twitter_keywords_file, 'r') as f:
            twitter_keywords = f.read().strip()

    return render_template(
        "jobs_periodic.html",
        disabled_jobs=disabled_jobs,
        enabled_jobs=enabled_jobs,
        spiders=SPIDERS,
        settings=settings.to_dict(),
        twitter_usernames=twitter_usernames,
        twitter_keywords=twitter_keywords,
    )


@app.route("/jobs/completed", defaults={"page": 1})
@app.route("/jobs/completed/<int:page>")
def jobs_completed(page):
    # completed_jobs = db.session.query(Jobs).filter(Jobs.spider_status > 1).order_by(Jobs.id.desc()).all()
    pagination = db.session.query(Jobs).filter(Jobs.spider_status > 1).order_by(Jobs.id.desc()).paginate(page, IPP)

    return render_template(
        "jobs_completed.html",
        # completed_jobs=completed_jobs,
        pagination=pagination,
        now=datetime.datetime.now(),
    )


@app.route("/job/add", methods=["POST"])
def job_add():
    try:
        selected_spiders = request.form.get("_selected_spiders", [])
        if selected_spiders:
            selected_spiders = selected_spiders.strip().split(',')
            scrape_type = int(request.form.get("scrape_type"))
            scrape_type = scrape_type if scrape_type in (0, 1, 2) else 0
            use_proxies = OK.YES if request.form.get("use_proxies", False) else OK.NO
            use_proxies = use_proxies if use_proxies in (0, 1) else 0
            # cron_minutes = int(request.form.get("cron_minutes"))
            # cron_hour = int(request.form.get("cron_hour"))
            # run_type = 0 if cron_minutes == 0 and cron_hour == 0 else 1
            # run_type = 0
            # repeat_time = 0
            # if run_type == 1:
            #     repeat_time = cron_hour * 60 + cron_minutes
        # print(selected_spiders)
        if len(selected_spiders) > 0:
            params = {
                "spider": None,
                "delay": int(request.form.get("delay", settings.delay)),
                "timeout": int(request.form.get("timeout", settings.timeout)),
                "retries": int(request.form.get("retries", settings.retries)),
                "concurrent_requests": settings.concurrent_requests,
                "scrape_type": int(request.form.get("scrape_type", settings.scrape_type)),
                "feed": 1 if request.form.get("feed", False) else 0,
                "db": 1 if request.form.get("db", False) else 0,
                "images": 1 if request.form.get("images", False) else 0,
                "use_proxies": 1 if request.form.get("use_proxies", False) else 0,
                "mongo_uri": settings.mongo_uri,
                "mongo_db": settings.mongo_db,
                "redis_host": REDIS_HOST,
                "redis_port": REDIS_PORT,
                "twitter_consumer_key": settings.twitter_consumer_key,
                "twitter_consumer_secret": settings.twitter_consumer_secret,
                "twitter_access_token_key": settings.twitter_access_token_key,
                "twitter_access_token_secret": settings.twitter_access_token_secret,
                "twitter_usernames": text_to_lines(request.form.get("twitter_usernames", '')),
                "twitter_keywords": text_to_lines(request.form.get("twitter_keywords", '')),
            }
            # pprint(params,indent=4)
            twitter_usernames_file = path.join(BASE_DIR, "data", "twitter_usernames.txt")
            with open(twitter_usernames_file, 'w') as f:
                f.write('\n'.join(params["twitter_usernames"]))
            twitter_keywords_file = path.join(BASE_DIR, "data", "twitter_keywords.txt")
            with open(twitter_keywords_file, 'w') as f:
                f.write('\n'.join(params["twitter_keywords"]))
            jobs = []
            for spider in selected_spiders:
                index = int(spider)
                if index < len(SPIDERS):
                    p = deepcopy(params)
                    p["spider"] = index
                    p["spider_name"] = SPIDERS[index][0]
                    # if run_type == 0:
                    job = Jobs(
                        task_id="",
                        spider_name=p["spider_name"],
                        spider_status=SpiderStatus.PENDING,
                        scrape_type=p["scrape_type"],
                        use_proxies=p["use_proxies"],
                        file=p["feed"],
                        db=p["db"],
                        images=p["images"],
                    )
                    # else:
                    #     job = PeriodicJobs(
                    #         spider_name=p["spider_name"],
                    #         scrape_type=scrape_type,
                    #         use_proxies=use_proxies,
                    #         file=p["feed"],
                    #         db=p["db"],
                    #         images=p["images"],
                    #         enabled=OK.YES,
                    #         repeat_time=repeat_time,
                    #         date_started=datetime.datetime.now(),
                    #     )
                    jobs.append((job, p))
            if jobs:
                for j, p in jobs:
                    db.session.add(j)
                db.session.commit()
                # if run_type == 0:  # Onetime job
                flash("Successfully added {} scrape job(s)".format(len(jobs)), "success")
                for j, p in jobs:
                    task_id = run_job.delay(j.id, p)
                    # pprint(p, indent=4)
                    # print(task_id)
                # else:  # Periodic job
                #     for j, p in jobs:
                #         try:
                #             scheduler.add_job(
                #                 func=run_periodic_job.delay,
                #                 trigger=IntervalTrigger(seconds=repeat_time),
                #                 id=j.spider_name,
                #                 args=(j.id, p),
                #                 name=j.spider_name,
                #                 replace_existing=True,
                #             )
                #             db.session.add(j)
                #             flash("Successfully added periodic job {}".format(j.id), "success")
                #         except ConflictingIdError:
                #             flash("Job id {} already exists".format(j.id), "danger")
                #         except Exception as e:
                #             flash("Failed starting the job id {}, details: {}".format(j.id, e))
                #     # flash("Successfully added {} periodic scrape job(s)".format(len(jobs)), "success")
        else:
            flash("Please select at least one spider", "warning")
    except Exception as e:
        flash("Failed adding scrape job, details: {}".format(e), "danger")

    return redirect(request.referrer)


@app.route("/jobs/<int:job_id>/stop")
def job_stop(job_id):
    job = db.session.query(Jobs).filter(Jobs.id == job_id).first()
    if job is None:
        flash("Can't find the job id {} in db".format(job_id), "danger")
    else:
        r = _redis.sadd("{}:stop".format(job.spider_name), job.task_id)
        logger.info("Stopping spider {} job id {}, redis response {}".format(job.spider_name, job.task_id, r))
        # print(int(SpiderStatus.CANCELED))
        job.spider_status = int(SpiderStatus.CANCELED)
        db.session.commit()

    return redirect("/jobs/active/{}".format(job_id))


@app.route("/periodic-jobs/add", methods=["POST"])
def periodic_jobs_add():
    try:
        selected_spiders = request.form.get("_selected_spiders", [])
        if selected_spiders:
            selected_spiders = selected_spiders.strip().split(',')
            scrape_type = int(request.form.get("scrape_type"))
            scrape_type = scrape_type if scrape_type in (0, 1, 2) else 0
            use_proxies = OK.YES if request.form.get("use_proxies", False) else OK.NO
            use_proxies = use_proxies if use_proxies in (0, 1) else 0
            cron_minutes = int(request.form.get("cron_minutes"))
            cron_hour = int(request.form.get("cron_hour"))
            if cron_minutes == 0 and cron_hour == 0:
                flash("Please choose repeat time", "warning")
                return redirect("/jobs/periodic")
            repeat_time = cron_hour * 60 + cron_minutes
        if len(selected_spiders) > 0:
            params = {
                "spider": None,
                "delay": int(request.form.get("delay", settings.delay)),
                "timeout": int(request.form.get("timeout", settings.timeout)),
                "retries": int(request.form.get("retries", settings.retries)),
                "concurrent_requests": settings.concurrent_requests,
                "scrape_type": int(request.form.get("scrape_type", settings.scrape_type)),
                "feed": 1 if request.form.get("feed", False) else 0,
                "db": 1 if request.form.get("db", False) else 0,
                "images": 1 if request.form.get("images", False) else 0,
                "use_proxies": 1 if request.form.get("use_proxies", False) else 0,
                "mongo_uri": settings.mongo_uri,
                "mongo_db": settings.mongo_db,
                "redis_host": REDIS_HOST,
                "redis_port": REDIS_PORT,
                "twitter_consumer_key": settings.twitter_consumer_key,
                "twitter_consumer_secret": settings.twitter_consumer_secret,
                "twitter_access_token_key": settings.twitter_access_token_key,
                "twitter_access_token_secret": settings.twitter_access_token_secret,
                "twitter_usernames": text_to_lines(request.form.get("twitter_usernames", '')),
                "twitter_keywords": text_to_lines(request.form.get("twitter_keywords", '')),
            }
            twitter_usernames_file = path.join(BASE_DIR, "data", "twitter_usernames.txt")
            with open(twitter_usernames_file, 'w') as f:
                f.write('\n'.join(params["twitter_usernames"]))
            twitter_keywords_file = path.join(BASE_DIR, "data", "twitter_keywords.txt")
            with open(twitter_keywords_file, 'w') as f:
                f.write('\n'.join(params["twitter_keywords"]))
            jobs = []
            for spider in selected_spiders:
                id_ = int(spider)
                index = id_ - 1
                # print(index)
                try:
                    job = db.session.query(PeriodicJobs).filter(PeriodicJobs.id == id_).first()
                    job.scrape_type = scrape_type
                    job.use_proxies = use_proxies
                    job.file = params["feed"]
                    job.db = params["db"]
                    job.images = params["images"]
                    job.repeat_time = repeat_time
                    job.enabled = OK.YES
                    db.session.commit()
                    p = deepcopy(params)
                    p["spider"] = index
                    p["spider_name"] = SPIDERS[index][0]
                    scheduler.add_job(
                        func=run_periodic_job.delay,
                        trigger=IntervalTrigger(minutes=repeat_time),
                        id=job.spider_name,
                        args=(job.id, p),
                        name=job.spider_name,
                        replace_existing=True,
                    )
                    flash("Successfully added periodic job {}".format(job.id), "success")
                except ConflictingIdError:
                    job.enabled = OK.NO
                    db.session.commit()
                    flash("Job id {} already exists".format(job.id), "danger")
                except Exception as e:
                    job.enabled = OK.NO
                    db.session.commit()
                    flash("Failed starting the job id {}, details: {}".format(job.id, e))
        else:
            flash("Please select at least one spider", "warning")
    except Exception as e:
        flash("Failed adding scrape job, details: {}".format(e), "danger")

    return redirect("/jobs/periodic")


@app.route("/periodic-jobs/<int:job_id>/start")
def periodic_job_start(job_id):
    job = db.session.query(PeriodicJobs).filter(PeriodicJobs.id == job_id).first()
    if job is None:
        flash("Can't find the job id {} in db".format(job_id), "danger")
    else:
        try:
            spider = None
            for i, s in enumerate(SPIDERS):
                if job.spider_name == s[0]:
                    spider = i
            if spider is None:
                raise Exception("Can't find spider {} id".format(job.spider_name))
            params = {
                "spider": spider,
                "spider_name": job.spider_name,
                "delay": settings.delay,
                "timeout": settings.timeout,
                "retries": settings.retries,
                "concurrent_requests": settings.concurrent_requests,
                "scrape_type": job.scrape_type,
                "feed": job.file,
                "db": job.db,
                "images": job.images,
                "use_proxies": job.use_proxies,
                "mongo_uri": settings.mongo_uri,
                "mongo_db": settings.mongo_db,
            }
            # print(params)
            scheduler.add_job(
                func=run_periodic_job.delay,
                trigger=IntervalTrigger(minutes=job.repeat_time),
                id=job.spider_name,
                args=(job.id, params),
                name=job.spider_name,
                replace_existing=True,
            )
            job.enabled = OK.YES
            db.session.commit()
            flash("Successfully added periodic job {}".format(job.id), "success")
        except ConflictingIdError:
            # job.enabled = OK.NO
            # db.session.commit()
            flash("Job id {} already exists".format(job.id), "danger")
        except Exception as e:
            # job.enabled = OK.NO
            # db.session.commit()
            flash("Failed starting the job id {}, details: {}".format(job.id, e))

    return redirect("/jobs/periodic")


@app.route("/periodic-jobs/<int:job_id>/stop")
def periodic_job_stop(job_id):
    job = db.session.query(PeriodicJobs).filter(PeriodicJobs.id == job_id).first()
    if job is None:
        flash("Can't find the job id {} in db".format(job_id), "danger")
    else:
        try:
            scheduler.remove_job(job.spider_name)
            job.enabled = OK.NO
            db.session.commit()
            flash("Successfully stopped periodic job {}".format(job_id), "success")
        except JobLookupError:
            job.enabled = OK.NO
            db.session.commit()
            flash("Can't find the job id {} in enabled jobs, moving it back to disabled ones".format(job_id), "danger")
        except Exception as e:
            flash("Failed stopping the job id {}, details: {}".format(job_id, e))

    return redirect("/jobs/periodic")


@app.route("/jobs/<int:job_id>/log")
def job_log(job_id):
    job = db.session.query(Jobs).filter(Jobs.id == job_id).first()
    if job is None:
        flash("Can't find the job id {} in db".format(job_id), "danger")
        # return redirect(request.referrer)
    else:
        file_name = "{} {}.log".format(job.spider_name, str(job.date_started).split('.')[0].strip())
        log_file = path.join(LOG_DIR, file_name)
        log_lines = []
        ok = False
        if path.isfile(log_file):
            with open(log_file, 'r') as f:
                for line in f.readlines():
                    log_lines.append(line.strip())
        else:
            flash("Can't locate the log file {}".format(log_file), "danger")

    return render_template(
        "job_log.html",
        log_lines=log_lines,
    )


@app.route("/spiders/<int:job_id>/feed")
def job_feed(job_id):
    job = db.session.query(Jobs).filter(Jobs.id == job_id).first()
    if job is None:
        flash("Can't find the job id {} in db".format(job_id), "danger")
    else:
        file_name = "{} {}.json".format(job.spider_name, str(job.date_started).split('.')[0].strip())
        feed_file = path.join(FEEDS_DIR, file_name)
        feed_lines = []
        ok = False
        if path.isfile(feed_file):
            with open(feed_file, 'r') as f:
                for line in f.readlines():
                    feed_lines.append(line.strip())
        else:
            flash("Can't locate the JSON feed file {}".format(feed_file), "danger")

    return render_template(
        "spider_feed.html",
        feed_lines=feed_lines,
    )


@app.route("/project/settings", methods=["GET", "POST"])
def project_settings():
    global settings
    if request.method == "POST":
        try:
            settings.delay = int(request.form.get("delay"))
            settings.timeout = int(request.form.get("timeout"))
            settings.retries = int(request.form.get("retries"))
            settings.concurrent_requests = int(request.form.get("concurrent_requests"))
            settings.scrape_type = int(request.form.get("scrape_type"))
            settings.feed = 1 if request.form.get("feed", False) else 0
            settings.db = 1 if request.form.get("db", False) else 0
            settings.images = 1 if request.form.get("images", False) else 0
            settings.use_proxies = 1 if request.form.get("use_proxies", False) else 0
            settings.mongo_uri = request.form.get("mongo_uri")
            settings.mongo_db = request.form.get("mongo_db")
            settings.twitter_consumer_key = request.form.get("twitter_consumer_key")
            settings.twitter_consumer_secret = request.form.get("twitter_consumer_secret")
            settings.twitter_access_token_key = request.form.get("twitter_access_token_key")
            settings.twitter_access_token_secret = request.form.get("twitter_access_token_secret")
            settings.save(SETTINGS_FILE)
            flash("Successfully updated settings", "success")
        except Exception as e:
            flash("Failed updating settings, details: {}".format(e), "danger")
        return redirect("/project/settings")

    return render_template(
        "project_settings.html",
        settings=settings.to_dict(),
    )


@app.route("/project/spiders")
def project_spiders():
    twitter_usernames_file = path.join(BASE_DIR, "data", "twitter_usernames.txt")
    twitter_usernames = ''
    if path.isfile(twitter_usernames_file):
        with open(twitter_usernames_file, 'r') as f:
            twitter_usernames = f.read().strip()
    twitter_keywords_file = path.join(BASE_DIR, "data", "twitter_keywords.txt")
    twitter_keywords = ''
    if path.isfile(twitter_keywords_file):
        with open(twitter_keywords_file, 'r') as f:
            twitter_keywords = f.read().strip()

    spiders = [(i, spider[0], spider[1]) for i, spider in enumerate(SPIDERS)]

    return render_template(
        "project_spiders.html",
        spiders=spiders,
        settings=settings.to_dict(),
        twitter_usernames=twitter_usernames,
        twitter_keywords=twitter_keywords,
    )


@app.route("/project/ua", methods=["GET", "POST"])
def project_ua():
    ua_file = path.join(BASE_DIR, "data", "user_agents.txt")
    user_agents = ''
    ok = False
    if request.method == "POST":
        user_agents = request.form.get("user-agents", None)
        with open(ua_file, 'w') as f:
            f.write(user_agents.strip() + '\n')
            flash("Successfully updated user agents list", "success")
    else:
        if path.isfile(ua_file):
            with open(ua_file, 'r') as f:
                user_agents = f.read().strip()

    return render_template(
        "project_ua.html",
        user_agents=user_agents,
    )


@app.route("/project/proxies", methods=["GET", "POST"])
def project_proxies():
    proxies_file = path.join(BASE_DIR, "data", "proxies.txt")
    proxies = ''
    ok = False
    if request.method == "POST":
        proxies = request.form.get("proxies", None)
        with open(proxies_file, 'w') as f:
            f.write(proxies.strip() + '\n')
            flash("Successfully updated proxies", "success")
    else:
        if path.isfile(proxies_file):
            with open(proxies_file, 'r') as f:
                proxies = f.read().strip()

    return render_template(
        "project_proxies.html",
        proxies=proxies,
    )


if __name__ == "__main__":
    if WEBUI_LOGGING:
        formatter = logging.Formatter("[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s")
        log_file = path.join(LOG_DIR, "webui {}.log".format(strftime("%Y-%m-%d %H:%M:%S")))
        handler = RotatingFileHandler(log_file, maxBytes=1024 * 1024 * 10, backupCount=2)
        handler.setLevel(logging.WARNING)
        handler.setFormatter(formatter)
        app.logger.addHandler(handler)
        app.logger.setLevel(logging.WARNING)
    app.run(host=WEBUI_HOST, port=WEBUI_PORT, debug=DEBUG)
