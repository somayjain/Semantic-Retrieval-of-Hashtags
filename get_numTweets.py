from whoosh.index import open_dir

ix = open_dir("index")
searcher = ix.searcher()
numdocs = searcher.doc_count()
print numdocs