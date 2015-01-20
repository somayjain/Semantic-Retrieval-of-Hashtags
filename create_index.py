
import os.path
from whoosh.index import create_in
from whoosh.fields import Schema, TEXT, KEYWORD, ID
from collections import namedtuple
from whoosh.analysis import StemmingAnalyzer

Tweet = namedtuple('Tweet', 'label tweet_id date label_query author text')
Hashtags = namedtuple('Hashtags','hashtag_list hashtag_segmentations')

stem_ana = StemmingAnalyzer()

schema = Schema(tweet_id=ID(stored=True),
    author=TEXT(stored=True),
    tweet=TEXT(analyzer=stem_ana, stored=True),
    # orig_hashtags=KEYWORD(stored=True, commas=True, scorable=True),
    orig_hashtags=TEXT(stored=True),
    seg_hashtags=TEXT(stored=True),
    abstract_text=TEXT(analyzer=stem_ana, stored=False),
    abstract_title=TEXT(stored=False))

def read_data(data_path):
    with open(data_path) as file:
        for line in file:
            tweet, hashtags, abstract = eval(line)
            abstract = [selected for selected in abstract["annotations"] if float(selected['rho']) >= 0.10]
            yield tweet, hashtags, abstract

def enc(inp):
    
    # try:
    #     print "try1", inp
    #     inp = inp.encode("utf-8")
    # except:
    #     # try:
    #         print "try2", inp
    #         inp = inp.decode("utf-8", "replace")
    #     # except:
    #         print "except", inp
    #         # inp = unicode(inp)
    #         # pass
    # print inp
    try:
        return inp.decode("utf-8", "replace")
    except:
        return unicode(inp)
        # return inp.decode("ascii", "replace")
    


if not os.path.exists("index"):
    os.mkdir("index")
ix = create_in("index", schema)

writer = ix.writer()
# Add to the writer here.
for tweet, hashtag, abstract in read_data('tagmed_data.out'):
    try:
        writer.add_document(tweet=enc(tweet.text),
        tweet_id=enc(tweet.tweet_id),
        author=enc(tweet.author),
        orig_hashtags=u" ".join(map(lambda x: enc(x), hashtag.hashtag_list)),
        seg_hashtags=u" ".join(map(lambda x: enc(x), hashtag.hashtag_segmentations)) if hashtag.hashtag_segmentations and hashtag.hashtag_segmentations[0] else u'',
        abstract_text=u' '.join([enc(dictionary['abstract']) for dictionary in abstract]) if abstract else u'',
        abstract_title=u' '.join([enc(dictionary['title']) for dictionary in abstract]) if abstract else  u'')
    except:
        print tweet
        pass
        



# Commit when done
writer.commit()