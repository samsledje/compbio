#!/usr/bin/env python
#
# SPIDIR - SPecies Informed DIstance-based Reconstruction
# Matt Rasmussen
# May 2006
#

# python libs
import copy
import math
import os
import random
import StringIO
import sys

# rasmus libs
from rasmus import genomeutil
from rasmus import fasta
from rasmus import phylip
from rasmus import phyloutil
from rasmus import stats
from rasmus import treelib
from rasmus import util

# spidir lib
from rasmus import spidirlib



# command line options
options = ["""\
  SPIDIR v0.5  Oct 2006
  SPecies Informed DIstanced-base Reconstruction
    by Matt Rasmussen 
    
""",
 "Options",
 ["o:", "out=", "out", "<output prefix>",
    {"help": "The prefix for all output files", 
     "single": True,
     "default": "spidir"}],
 
 ["d:", "dist=", "dist", "<distance file>", 
    {"help": "Build a tree from a phylip distance matrix file"}],

 ["l:", "labels=", "labels", "<gene labels file>", 
    {"help": "Supply gene names for the rows and cols of a distance matrix"}],
     
 ["p:", "param=", "param", "<param file>",
    {"help": "When training this is used as an output file",
     "single": True,
     "req": True}],
 ["s:", "stree=", "stree", "<species tree>",
    {"single": True,
     "req": True,
     "help": "species tree (newick format)"}],
 ["S:", "smap=", "smap", "<gene2species map>",
    {"req": True,
     "help": "mapping of gene names to species names"}],

 #["a:", "align=", "align", "<fasta alignment>",
 #   {"help": "Build a tree from a multiple sequence alignment in fasta format"}],
     
 
 "Search options",
 ["R:", "search=", "search", "<method>",
    {"default": ["mcmc"],
     "help": """\
    tree search method.  Options are:
        mcmc   - Markov Chain Monte Carlo (default)
        greedy - Phylip-like search
        none   - no search"""}],
 ["T:", "tree=", "tree", "<propose tree>",
    {"default": []}],
 ["i:", "iters=", "iters", "<MCMC iterations>", 
    {"default": 1000, 
     "parser": int,
     "single": True}],
 ["I:", "depth=", "depth", "<greedy NNI depth>",
    {"default": 3,
     "parser": int,
     "single": True}],
 
 ["", "rerootprob=", "rerootprob", "<probability of reroot>",
    {"single": True,
     "default": 1,
     "parser": float}],
 ["", "nchains=", "nchains", "<number of chains>",
    {"single": True,
     "default": 2,
     "parser": int}],
 ["", "eprune=", "eprune", "<exhaustive prune>",
    {"single": True,
     "default": -10,
     "parser": float}],
 ["", "searchtest", "searchtest", "",
    {"single": True}],
 ["", "regrafts=", "regrafts", "<regraph iterations>",
    {"single": True,
     "parser": int,
     "default": 100}],
 
 # OLD search parameters
 #
 #["", "hilliters=", "hilliters", "<number of hill climbs>",
 #   {"single": True,
 #    "default": 20,
 #    "parser": int}],
 #["", "maxiters=", "maxiters", "<maximum iterations>", 
 #   {"default": 5000, 
 #    "parser": int,
 #    "single": True}], 
 #["", "speedup=", "speedup", "<speed up factor>",
 #   {"single": True,
 #    "default": 0.0,
 #    "parser": float}],
 #["", "maxerror=", "maxerror", "<maximum allowed rel error>",
 #   {"single": True,
 #    "default": .2,
 #    "parser": float}],
 #["", "toptrees=", "toptrees", "<number of trees for consensus>",
 #   {"single": True,
 #    "default": 100,
 #    "parser": int}],

 "Training options",
 ["t", "train", "train", "",
    {"help": """\
    Run SPIDIR in training mode.  """,
    "single":True}],
 ["z:", "trainstats=", "trainstats", "<training stats prefix>",
    {"single": True,
     "default": ""}],
 #["e:", "trainext=", "trainext", "<training tree extension>",
 #   {"single":True}],
 
 "Parameter options",
 ["D:", "dupprob=", "dupprob", "<probability of duplication>",
    {"default": 1,
     "parser": float,
     "single": True}],
 ["L:", "lossprob=", "lossprob", "<probability of loss>",
    {"default": 1,
     "parser": float,
     "single": True}],
 ["", "errorcost=", "errorcost", "<error cost>",
    {"single": True,
     "default": -80,
     "parser": float}],
 
 "Miscellaneous options",
 ["", "correcttree=", "correcttree", "<correct tree newick>",
    {"single": True,
     "parser": treelib.readTree}],
 ["V:", "debug=", "debug", "<level>",
    {"single": True,
     "default": 0, 
     "parser": int,
     "help": "set SPIDIR debug level"}],

 ["P:", "paths=", "paths", "<files path>",
    {"single": True,
     "help": "colon separated paths used to search for data files",
     "default": "."}]
]

# import spidirlib's debug function
debug = spidirlib.debug


def main(argv):   
    # parse options
    conf = util.parseOptions(argv, options, quit=True)

    # setup debug output
    #spidirlib.setDebugStream(file(spidirlib.debugFile(conf), "w"))
    
    if conf["debug"] > 0:
        util.globalTimer().removeStream(sys.stderr)
        util.globalTimer().addStream(sys.stdout)
        debug("SPIDIR")
        debug("configuration:")
        util.printDict(conf, justify=lambda x: "left", out=spidirlib.DEBUG)
        debug()
        debug()
    
    
    genomeutil.readOptions(conf)
    conf["specprob"] = 1.0 - conf["dupprob"]
    
    # read input
    gene2species = conf["gene2species"]
    stree = conf["stree"]
    
    if conf["train"]:
        trainTree(conf, stree, gene2species)
    else:
        buildTree(conf, stree, gene2species)




def trainTree(conf, stree, gene2species):
    treefiles = conf[""] 
    #util.listFiles(conf["traindir"], conf["trainext"])

    util.tic("reading trees")
    trees = []
    prog = util.ProgressBar(len(treefiles))
    for treefile in treefiles:
        prog.update()
        trees.append(treelib.readTree(treefile))
    util.toc()
    
    params = spidirlib.learnModel(trees, stree, gene2species, conf["trainstats"])
    
    spidirlib.writeParams(conf["param"], params)
    
    


def buildTree(conf, stree, gene2species):
    params = spidirlib.readParams(conf["param"])
    
    if "correcttree" in conf:
        conf["correcthash"] = phyloutil.hashTree(conf["correcttree"])
    
    
    if "dist" in conf:
        for i in range(len(conf["dist"])):
            distfile = conf["dist"][i]
            
            labels, distmat = phylip.readDistMatrix(distfile)
        
            # read in different labels if needed
            if "labels" in conf:
                labels = spidirlib.readLabels(conf["labels"][i])
            
            tree, logl = spidirlib.sindir(conf, distmat, labels, stree, 
                                          gene2species, params)
            tree.write(spidirlib.outTreeFile(conf))
            
            # test for correctness
            if "correcttree" in conf:
                correctTree = conf["correcttree"]
                phyloutil.hashOrderTree(correctTree)
                phyloutil.hashOrderTree(tree)
                
                thash1 = phyloutil.hashTree(tree)
                thash2 = phyloutil.hashTree(correctTree)
                
                print "spidir: "
                treelib.drawTree(tree, maxlen=5, minlen=5)
                print
                
                print "correct:"
                treelib.drawTree(correctTree, maxlen=5, minlen=5)
                print
                
                rferror = spidirlib.robinsonFouldsError(correctTree, tree)
                
                if thash1 == thash2:
                    print "CORRECT TREE FOUND"
                else:
                    print "WRONG TREE FOUND (RF: %f)" % rferror
            


#
# run as script
#
if __name__ == "__main__":
    try:
        main(sys.argv)
    except util.OptionError, e:
        print >>sys.stdout, "%s: %s" % (os.path.basename(sys.argv[0]), e)
        sys.exit(1)



