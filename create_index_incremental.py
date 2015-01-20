
import sys
import whoosh.index as index
from whoosh.fields import Schema, TEXT, KEYWORD, ID
from collections import namedtuple
from whoosh.analysis import StemmingAnalyzer

Tweet = namedtuple('Tweet', 'label tweet_id date label_query author text')
Hashtags = namedtuple('Hashtags','hashtag_list hashtag_segmentations')

def read_data(data_path):
    with open(data_path) as file:
        for line in file:
            if line == "\n":
                continue
            tweet, hashtags, abstract = eval(line)
            abstract = [selected for selected in abstract["annotations"] if float(selected['rho']) >= 0.10]
            yield tweet, hashtags, abstract

def enc(inp):
    
    try:
        return inp.decode("utf-8", "replace")
    except:
        return unicode(inp)
        # return inp.decode("ascii", "replace")
    

ix = index.open_dir("index")
count = 0
writer = ix.writer()
# Add to the writer here.
for tweet, hashtag, abstract in read_data(sys.argv[1]):
    try:
        writer.add_document(tweet=enc(tweet.text),
        tweet_id=enc(tweet.tweet_id),
        author=enc(tweet.author),
        orig_hashtags=u" ".join(map(lambda x: enc(x), hashtag.hashtag_list)),
        seg_hashtags=u" ".join(map(lambda x: enc(x), hashtag.hashtag_segmentations)) if hashtag.hashtag_segmentations and hashtag.hashtag_segmentations[0] else u'',
        abstract_text=u' '.join([enc(dictionary['abstract']) for dictionary in abstract]) if abstract else u'',
        abstract_title=u' '.join([enc(dictionary['title']) for dictionary in abstract]) if abstract else  u'')
        count += 1
    except:
        print tweet
        pass
        
# Commit when done
print "Done ", sys.argv[1], count
writer.commit()