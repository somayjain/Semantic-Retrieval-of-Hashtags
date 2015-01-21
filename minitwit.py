# -*- coding: utf-8 -*-
"""
    MiniTwit
    ~~~~~~~~

    A microblogging application written with Flask and sqlite3.

    :copyright: (c) 2015 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""

import time
from sqlite3 import dbapi2 as sqlite3
from hashlib import md5
from datetime import datetime
from flask import Flask, request, session, url_for, redirect, \
     render_template, abort, g, flash, _app_ctx_stack
from werkzeug import check_password_hash, generate_password_hash

from math import pow, log

from whoosh.index import open_dir
from whoosh.qparser import QueryParser, MultifieldParser, OrGroup, AndGroup, AndMaybeGroup
from whoosh import scoring
from whoosh.classify import *

# configuration
DATABASE = 'minitwit.db'
PER_PAGE = 30
DEBUG = False
SECRET_KEY = 'development key'

# create our little application :)
app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('MINITWIT_SETTINGS', silent=True)

NUM_RESULTS = 10
# NUM_DOCS = 250
MIN_DOCS = 250
PERCENT = 3
NUM_HASHTAGS = 10

# Semantic search fields
search_fields = ["tweet", "orig_hashtags", "seg_hashtags", "abstract_text"]

def search_semantic_query(query_str):
    ix = open_dir("index")
    with ix.searcher() as searcher:
        query = MultifieldParser(search_fields, ix.schema).parse(query_str)
        results = searcher.search(query, limit=None)
        
        query = MultifieldParser(search_fields, ix.schema, group=OrGroup).parse(query_str)
        results2 = searcher.search(query, limit=None)

        results2.upgrade(results)
        results = results2

        # flash("Semantic" + str(len(results)))

        if len(results) == 0:
            return []
        else:
            tweets = []
            for i in (range(min(NUM_RESULTS, len(results)))):
                tweets.append(results[i]["tweet"])
            return tweets

def search_baseline_query(query_str):
    ix = open_dir("index")
    with ix.searcher() as searcher:
        query = QueryParser("tweet", ix.schema).parse(query_str)
        results = searcher.search(query, limit=None)

        query = QueryParser("tweet", ix.schema, group=OrGroup).parse(query_str)
        results2 = searcher.search(query, limit=None)
        results2.upgrade(results)
        results = results2

        # flash("Baseline" + str(len(results)))

        if len(results) == 0:
            return []
        else:
            tweets = []
            for i in (range(min(NUM_RESULTS, len(results)))):
                tweets.append(results[i]["tweet"])
            return tweets

def getRelativeRecall(query_str):
    ix = open_dir("index")
    with ix.searcher() as searcher:
        query = QueryParser("tweet", ix.schema).parse(query_str)
        results = searcher.search(query, limit=None)

        query = QueryParser("tweet", ix.schema, group=OrGroup).parse(query_str)
        results2 = searcher.search(query, limit=None)
        
        results2.upgrade(results)
        results = results2

        results_baseline = results
        results_baseline = [result["tweet"] for result in results_baseline]
    
        query = MultifieldParser(search_fields, ix.schema).parse(query_str)
        results = searcher.search(query, limit=None)
        
        query = MultifieldParser(search_fields, ix.schema, group=OrGroup).parse(query_str)
        results2 = searcher.search(query, limit=None)

        results2.upgrade(results)
        results = results2

        results_semantic = results
        results_semantic = [result["tweet"] for result in results_semantic]
    
        num_common = len(list(set(results_baseline) & set(results_semantic)))
        # flash("Common " + str(num_common))
        recall = {}
        if num_common != 0:
            if (len(results_semantic) + num_common) == 0:
                recall = 0.0
            else:
                recall = (1.0*len(results_semantic))/(len(results_semantic) + num_common)
        else:
            if (len(results_baseline) + len(results_semantic)) == 0:
                recall = 0
            else:
                recall = (1.0*len(results_semantic))/(len(results_baseline) + len(results_semantic))
        return recall


def search_hashtag_query(query_str):
    ix = open_dir("index")
    
    with ix.searcher() as searcher:
    # with ix.searcher(weighting=scoring.TF_IDF()) as searcher:
        query = QueryParser("orig_hashtags", ix.schema, group=OrGroup).parse(query_str)
        # query = QueryParser("tweet", ix.schema).parse(query_str)
        # search_fields = ["tweet"]
        # query = MultifieldParser(search_fields, ix.schema).parse(query_str)
        results = searcher.search(query, limit=None)
        if len(results) == 0:
            return []
        else:
            tweets = []
            for i in (range(min(NUM_RESULTS, len(results)))):
                tweets.append(results[i]["tweet"])
            return tweets

def hashtag_retrieval_semantic(query_str):
    ix = open_dir("index")
    
    with ix.searcher() as searcher:
    # with ix.searcher(weighting=scoring.TF_IDF()) as searcher:
        query = MultifieldParser(search_fields, ix.schema).parse(query_str)
        results = searcher.search(query, limit=None)
        results_and = results
        
        query = MultifieldParser(search_fields, ix.schema, group=OrGroup).parse(query_str)
        results2 = searcher.search(query, limit=None)

        results2.upgrade(results)
        results = results2
        
        # flash("Semantic" + str(len(results)))
        if len(results) == 0:
            return []
        else:
            # NUM_DOCS = max(MIN_DOCS, PERCENT*len(results)/100)
            NUM_DOCS = max(MIN_DOCS, 50*len(results_and)/100)
            # flash("Semantic numdocs " + str(NUM_DOCS))
            # Hashtag retreival
            keywords = [keyword for keyword, score in results.key_terms("orig_hashtags", docs=NUM_DOCS, numterms=NUM_HASHTAGS, model=Bo1Model)]
            # keywords = results.key_terms("orig_hashtags", docs=NUM_DOCS, numterms=NUM_HASHTAGS, model=Bo1Model)
            print "Bo1Model", keywords
            keywords = [keyword for keyword, score in results.key_terms("orig_hashtags", docs=NUM_DOCS, numterms=NUM_HASHTAGS, model=Bo2Model)]
            print "Bo2Model", keywords
            
            keywords = [keyword for keyword, score in results.key_terms("orig_hashtags", docs=NUM_DOCS, numterms=NUM_HASHTAGS, model=KLModel)]
            print "KLModel", keywords
            
            return keywords

def hashtag_retrieval_baseline(query_str):
    ix = open_dir("index")
    
    with ix.searcher() as searcher:
    # with ix.searcher(weighting=scoring.TF_IDF()) as searcher:
        query = QueryParser("tweet", ix.schema).parse(query_str)
        results = searcher.search(query, limit=None)

        query = QueryParser("tweet", ix.schema, group=OrGroup).parse(query_str)
        results2 = searcher.search(query, limit=None)
        
        results2.upgrade(results)
        results = results2
        
        # flash("Baseline" + str(len(results)))
        
        if len(results) == 0:
            return []
        else:
            NUM_DOCS = max(MIN_DOCS, PERCENT*len(results)/100)
            # flash("Baseline numdocs " + str(NUM_DOCS))
            # Hashtag retreival
            keywords = [keyword for keyword, score in results.key_terms("orig_hashtags", docs=NUM_DOCS, numterms=NUM_HASHTAGS, model=Bo1Model)]
            # keywords = results.key_terms("orig_hashtags", docs=NUM_DOCS, numterms=NUM_HASHTAGS, model=Bo1Model)
            print "Bo1Model", keywords
            keywords = [keyword for keyword, score in results.key_terms("orig_hashtags", docs=NUM_DOCS, numterms=NUM_HASHTAGS, model=Bo2Model)]
            print "Bo2Model", keywords
            
            keywords = [keyword for keyword, score in results.key_terms("orig_hashtags", docs=NUM_DOCS, numterms=NUM_HASHTAGS, model=KLModel)]
            print "KLModel", keywords

            return keywords

def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    top = _app_ctx_stack.top
    if not hasattr(top, 'sqlite_db'):
        top.sqlite_db = sqlite3.connect(app.config['DATABASE'])
        top.sqlite_db.row_factory = sqlite3.Row
    return top.sqlite_db


@app.teardown_appcontext
def close_database(exception):
    """Closes the database again at the end of the request."""
    top = _app_ctx_stack.top
    if hasattr(top, 'sqlite_db'):
        top.sqlite_db.close()


def init_db():
    """Initializes the database."""
    db = get_db()
    with app.open_resource('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()


@app.cli.command('initdb')
def initdb_command():
    """Creates the database tables."""
    init_db()
    print('Initialized the database.')


def query_db(query, args=(), one=False):
    """Queries the database and returns a list of dictionaries."""
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    return (rv[0] if rv else None) if one else rv


def get_user_id(username):
    """Convenience method to look up the id for a username."""
    rv = query_db('select user_id from user where username = ?',
                  [username], one=True)
    return rv[0] if rv else None


def format_datetime(timestamp):
    """Format a timestamp for display."""
    return datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d @ %H:%M')


def gravatar_url(email, size=80):
    """Return the gravatar image for the given email address."""
    return 'http://www.gravatar.com/avatar/%s?d=identicon&s=%d' % \
        (md5(email.strip().lower().encode('utf-8')).hexdigest(), size)


@app.before_request
def before_request():
    g.user = None
    if 'user_id' in session:
        g.user = query_db('select * from user where user_id = ?',
                          [session['user_id']], one=True)


@app.route('/')
def home():
    
    return render_template('home.html')

@app.route('/query-semantic')
def query_semantic():
    query = request.args.get('text')
    msg = []
    if query:
        msg = search_semantic_query(query)
        # flash(msg)
    return render_template('query-semantic.html', messages=msg)

@app.route('/query-baseline')
def query_baseline():
    query = request.args.get('text')
    msg = []
    if query:
        msg = search_baseline_query(query)
        # flash(msg)
    return render_template('query-baseline.html', messages=msg)

@app.route('/query-hashtag')
def query_hashtag():
    query = request.args.get('text')
    msg = []
    if query:
        msg = search_hashtag_query(query)
        # flash(msg)
    return render_template('query-hashtag.html', messages=msg)

@app.route('/eval')
def evaluate():
    
    query = request.args.get('text')
    queryLen = 0
    results_left = []
    results_right = []
    recall = 0
    if query:
        queryLen = len(query)
        results_left = search_baseline_query(query)
        results_right = search_semantic_query(query)

        recall = getRelativeRecall(query)
    return render_template('eval.html', query=query, queryLen=queryLen, recall=recall, 
                            lenL=len(results_left), lenR=len(results_right),
                            results_left=results_left, results_right=results_right)

@app.route('/microblog_retrieval')
def microblog_retrieval():
    
    query = request.args.get('text')
    results_left = []
    results_right = []
    if query:
        results_left = search_baseline_query(query)
        results_right = search_semantic_query(query)
    return render_template('microblog_retrieval.html', query=query,
                            results_left=results_left, results_right=results_right)

@app.route('/hashtag_retrieval_eval')
def hashtag_retrieval_eval():
    
    query = request.args.get('text')
    queryLen = 0
    hashtags_left = []
    hashtags_right = []
    if query:
        queryLen = len(query)
        hashtags_left = hashtag_retrieval_baseline(query)
        hashtags_right = hashtag_retrieval_semantic(query)
    return render_template('hashtag_retrieval_eval.html', query=query, queryLen=queryLen,
                            hashtags_left=hashtags_left, hashtags_right=hashtags_right)

# For the screenshot of hashtags
@app.route('/hashtag_retrieval')
def hashtag_retrieval():
    
    query = request.args.get('text')
    hashtags_left = []
    hashtags_right = []
    if query:
        hashtags_left = hashtag_retrieval_baseline(query)
        hashtags_right = hashtag_retrieval_semantic(query)
    return render_template('hashtag_retrieval.html', query=query,
                            hashtags_left=hashtags_left, hashtags_right=hashtags_right)

def computeAP(ratings):
    # Invalid (No results found)
    if len(ratings) == 0:
        return 0
    isRelevant = map(lambda x: int(x)>=4, ratings)
    numRelevant = []
    AP = 0
    for i in range(len(isRelevant)):
        if i==0:
            numRelevant.append(isRelevant[0])
        else:
            numRelevant.append(isRelevant[i] + numRelevant[i-1])
    
    den = numRelevant[-1]
    for i in range(len(isRelevant)):
        numRelevant[i] = (1.0* numRelevant[i] * isRelevant[i])/(i+1)
        AP += numRelevant[i]
    if den == 0:
        return 0
    else:
        return AP/den

# Reciprocal Rank
def computeRR(ratings):
    # Invalid (No results found)
    if len(ratings) == 0:
        return 0
    isRelevant = map(lambda x: int(x)>=4, ratings)
    for i in range(len(isRelevant)):
        if isRelevant[i] == 1:
            return 1.0/(i+1)
    return 0.0

def computeNDCG(ratings):
    # Invalid (No results found)
    if len(ratings) == 0:
        return 0
    ratings = map(lambda x: int(x), ratings)
    DCG = []
    for i in range(len(ratings)):
        x = ratings[i]
        temp = (pow(2, x) - 1.0)/(log(i+2, 2))
        DCG.append(temp)
        if i!=0:
            DCG[i] += DCG[i-1]
    ratings.sort()
    ratings.reverse()
    IDCG = []
    for i in range(len(ratings)):
        x = ratings[i]
        temp = (pow(2, x) - 1.0)/(log(i+2, 2))
        IDCG.append(temp)
        if i!=0:
            IDCG[i] += IDCG[i-1]
    return DCG[-1]/IDCG[-1]

@app.route('/submit_rating', methods=['POST'])
def submit_rating():
    query = request.form['query']
    recall = float(request.form['recall'])
    print "Recall", recall
    left_rating = request.form.getlist('left_rating')
    right_rating = request.form.getlist('right_rating')
    
    # Precision at N
    # lnumRelevant = reduce(lambda x, y:x+y, map(lambda x: int(x)>=4, left_rating))
    # rnumRelevant = reduce(lambda x, y:x+y, map(lambda x: int(x)>=4, right_rating))
    # lnumRelevant = (1.0*lnumRelevant)/NUM_RESULTS
    # rnumRelevant = (1.0*rnumRelevant)/NUM_RESULTS

    # Compute AP
    left_AP = computeAP(left_rating)
    right_AP = computeAP(right_rating)

    # Compute Reciprocal Rank
    left_RR = computeRR(left_rating)
    right_RR = computeRR(right_rating)

    # Compute NDCG
    leftNDCG = computeNDCG(left_rating)
    rightNDCG = computeNDCG(right_rating)

    print left_AP, right_AP
    print left_RR, right_RR
    print leftNDCG, rightNDCG

    # # Insert them into DB now.
    db = get_db()
    db.execute('''insert into search_score (query, recall, baseline_AP, semantic_AP, 
        baseline_RR, semantic_RR, baseline_NDCG, semantic_NDCG)
      values (?, ?, ?, ?, ?, ?, ?, ?)''', (query, recall, left_AP, right_AP,
                            left_RR, right_RR, leftNDCG, rightNDCG))
    db.commit()
    return redirect(url_for('hashtag_retrieval_eval', text=query))

@app.route('/submit_hashtag_rating', methods=['POST'])
def submit_hashtag_rating():
    query = request.form['query']
    left_rating = request.form.getlist('left_rating')
    right_rating = request.form.getlist('right_rating')
    
    # Compute AP
    left_AP = computeAP(left_rating)
    right_AP = computeAP(right_rating)

    # Compute Reciprocal Rank
    left_RR = computeRR(left_rating)
    right_RR = computeRR(right_rating)

    # Compute NDCG
    leftNDCG = computeNDCG(left_rating)
    rightNDCG = computeNDCG(right_rating)

    print left_AP, right_AP
    print left_RR, right_RR
    print leftNDCG, rightNDCG

    # Insert them into DB now.
    db = get_db()
    db.execute('''insert into hashtag_score (query, baseline_AP, semantic_AP, 
        baseline_RR, semantic_RR, baseline_NDCG, semantic_NDCG)
      values (?, ?, ?, ?, ?, ?, ?)''', (query, left_AP, right_AP,
                            left_RR, right_RR, leftNDCG, rightNDCG))
    
    db.commit()
    flash("Your feedback has been recorded. Thanks!")
    return redirect(url_for('evaluate'))


@app.route('/public')
def public_timeline():
    """Displays the latest messages of all users."""
    return render_template('timeline.html', messages=query_db('''
        select message.*, user.* from message, user
        where message.author_id = user.user_id
        order by message.pub_date desc limit ?''', [PER_PAGE]))


@app.route('/<username>')
def user_timeline(username):
    """Display's a users tweets."""
    profile_user = query_db('select * from user where username = ?',
                            [username], one=True)
    if profile_user is None:
        abort(404)
    followed = False
    if g.user:
        followed = query_db('''select 1 from follower where
            follower.who_id = ? and follower.whom_id = ?''',
            [session['user_id'], profile_user['user_id']],
            one=True) is not None
    return render_template('timeline.html', messages=query_db('''
            select message.*, user.* from message, user where
            user.user_id = message.author_id and user.user_id = ?
            order by message.pub_date desc limit ?''',
            [profile_user['user_id'], PER_PAGE]), followed=followed,
            profile_user=profile_user)


@app.route('/<username>/follow')
def follow_user(username):
    """Adds the current user as follower of the given user."""
    if not g.user:
        abort(401)
    whom_id = get_user_id(username)
    if whom_id is None:
        abort(404)
    db = get_db()
    db.execute('insert into follower (who_id, whom_id) values (?, ?)',
              [session['user_id'], whom_id])
    db.commit()
    flash('You are now following "%s"' % username)
    return redirect(url_for('user_timeline', username=username))


@app.route('/<username>/unfollow')
def unfollow_user(username):
    """Removes the current user as follower of the given user."""
    if not g.user:
        abort(401)
    whom_id = get_user_id(username)
    if whom_id is None:
        abort(404)
    db = get_db()
    db.execute('delete from follower where who_id=? and whom_id=?',
              [session['user_id'], whom_id])
    db.commit()
    flash('You are no longer following "%s"' % username)
    return redirect(url_for('user_timeline', username=username))

@app.route('/add_message', methods=['POST'])
def add_message():
    """Registers a new message for the user."""
    if 'user_id' not in session:
        abort(401)
    if request.form['text']:
        msg = search_query(request.form['text'])
        # db = get_db()
        # db.execute('''insert into message (author_id, text, pub_date)
        #   values (?, ?, ?)''', (session['user_id'], request.form['text'],
        #                         int(time.time())))
        # db.commit()
        flash(msg)
        print url_for('timeline')
    return redirect(url_for('timeline'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Logs the user in."""
    if g.user:
        return redirect(url_for('timeline'))
    error = None
    if request.method == 'POST':
        user = query_db('''select * from user where
            username = ?''', [request.form['username']], one=True)
        if user is None:
            error = 'Invalid username'
        elif not check_password_hash(user['pw_hash'],
                                     request.form['password']):
            error = 'Invalid password'
        else:
            flash('You were logged in')
            session['user_id'] = user['user_id']
            return redirect(url_for('timeline'))
    return render_template('login.html', error=error)


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registers the user."""
    if g.user:
        return redirect(url_for('timeline'))
    error = None
    if request.method == 'POST':
        if not request.form['username']:
            error = 'You have to enter a username'
        elif not request.form['email'] or \
                '@' not in request.form['email']:
            error = 'You have to enter a valid email address'
        elif not request.form['password']:
            error = 'You have to enter a password'
        elif request.form['password'] != request.form['password2']:
            error = 'The two passwords do not match'
        elif get_user_id(request.form['username']) is not None:
            error = 'The username is already taken'
        else:
            db = get_db()
            db.execute('''insert into user (
              username, email, pw_hash) values (?, ?, ?)''',
              [request.form['username'], request.form['email'],
               generate_password_hash(request.form['password'])])
            db.commit()
            flash('You were successfully registered and can login now')
            return redirect(url_for('login'))
    return render_template('register.html', error=error)


@app.route('/logout')
def logout():
    """Logs the user out."""
    flash('You were logged out')
    session.pop('user_id', None)
    return redirect(url_for('public_timeline'))


# add some filters to jinja
app.jinja_env.filters['datetimeformat'] = format_datetime
app.jinja_env.filters['gravatar'] = gravatar_url

if __name__ == '__main__':
    app.run(port=80, host="0.0.0.0")

