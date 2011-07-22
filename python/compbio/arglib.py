"""
    arglib.py
    
    Ancestral recombination graph (ARG)

"""


#=============================================================================
# imports

from __future__ import division

# python libs
import random
from itertools import izip
from collections import defaultdict
import heapq
from math import *

# compbio libs
from . import fasta

# rasmus libs
from rasmus import treelib, util, stats



#=============================================================================
# Ancestral Reconstruction Graph

class CoalNode (object):

    def __init__(self, name="n", age=0, event="gene", pos=0):
        self.name = name
        self.parents = []
        self.children = []
        self.event = event
        self.age = age
        self.pos = pos        # recomb position
        self.data = {}

    def __repr__(self):
        return "<node %s>" % self.name

    def get_dist(self, parent_index):
        return self.parents[parent_index].age - self.age

    def get_dists(self):
        return [p.age - self.age for p in self.parents]

    def copy(self):
        node = CoalNode(self.name, age=self.age, event=self.event,
                        pos=self.pos)
        node.data = dict(self.data)
        return node

    def is_leaf(self):
        return len(self.children) == 0
    



class ARG (object):

    def __init__(self, start=0.0, end=1.0):
        self.root = None
        self.nodes = {}
        self.nextname = 1
        self.start = start
        self.end = end


    def __iter__(self):
        return self.nodes.itervalues()


    def __len__(self):
        """Returns number of nodes in tree"""
        return len(self.nodes)


    def __getitem__(self, name):
        """Returns node by name"""
        return self.nodes[name]


    def __setitem__(self, name, node):
        """Adds a node to the tree"""
        node.name = name
        self.add(node)


    def __contains__(self, name):
        """
        Returns True if node in ARG has name 'name'
        """
        return name in self.nodes


    def new_name(self):
        """
        Returns a new name for a node
        """
        name = self.nextname
        self.nextname += 1
        return name

    def add(self, node):
        """
        Adds a node to the ARG
        """
        self.nodes[node.name] = node
        return node

    def remove(self, node):
        """
        Removes a node from the ARG
        """
        for child in node.children:
            child.parents.remove(node)
        for parent in node.parents:
            parent.children.remove(node)
        del self.nodes[node.name]


    def rename(self, oldname, newname):
        node = self.nodes[oldname]
        node.name = newname
        del self.nodes[oldname]
        self.nodes[newname] = node


    def leaves(self, node=None):
        """
        Iterates over the leaves of the ARG
        """
        if node is None:
            for node in self:
                if len(node.children) == 0:
                    yield node
        else:
            for node in self.preorder(node):
                if len(node.children) == 0:
                    yield node


    def leaf_names(self, node=None):
        """
        Iterates over the leaf names of the ARG
        """
        if node is None:
            for node in self:
                if len(node.children) == 0:
                    yield node.name
        else:
            for node in self.preorder(node):
                if len(node.children) == 0:
                    yield node.name
            
        
    def postorder(self, node=None):
        """
        Iterates through nodes in postorder traversal
        """

        visit = defaultdict(lambda: 0)
        queue = list(self.leaves(node))

        for node in queue:
            yield node
            for parent in node.parents:
                visit[parent] += 1

                # if all children of parent has been visited then queue parent
                if visit[parent] == len(parent.children):
                    queue.append(parent)

        
    def preorder(self, node=None):
        """
        Iterates through nodes in preorder traversal
        """

        visit = set()
        if node is None:
            node = self.root
        queue = [node]

        for node in queue:
            if node in visit:
                continue
            yield node
            visit.add(node)
            
            for child in node.children:
                queue.append(child)
        

    #==============================

    def set_recomb_pos(self, start=None, end=None, descrete=False):
        """
        Set all recombination positions in the ARG
        """

        if start is not None:
            self.start = start
        if end is not None:
            self.end = end

        length = self.end - self.start

        for node in self:
            if node.event == "recomb":
                if descrete:
                    node.pos = random.randint(self.start, self.end-1) + .5
                else:
                    node.pos = random.random() * length + self.start

    
    def set_ancestral(self):
        """
        Set all ancestral regions for the nodes of the ARG

        NOTE: recombination positions must be set first (set_recomb_pos)
        """

        # NOTE: block_counts is used to determine when the MRCA of a block
        # is found.
        
        # get all non-recomb blocks (identified by starting pos)
        nleaves = len(list(self.leaves()))
        all_blocks = list(iter_recomb_blocks(self))
        block_counts = dict((block, nleaves) for block in all_blocks)

        for node in self.postorder():
            if node.is_leaf():
                # initialize leaves with entire extant sequence
                node.data["ancestral"] = list(all_blocks)
            elif node.event == "coal":
                # union of ancestral of children
                # get all child regions
                assert len(node.children) == 2, node
                
                # walk through regions for both children and determine
                # whether they coal
                if node.children[0] == node.children[1]:
                    # special case
                    regions1 = node.children[0].data["ancestral"]
                    regions2 = []
                else:
                    regions1 = self.get_ancestral(
                        node.children[0],parent=node)
                    regions2 = self.get_ancestral(
                        node.children[1],parent=node)
                regions3 = []

                i = j = 0
                while True:                        
                    reg1 = regions1[i] if i < len(regions1) else None
                    reg2 = regions2[j] if j < len(regions2) else None
                    if reg1 is None and reg2 is None:
                        # stop when all regions have been considered
                        break

                    if reg1 == reg2:
                        # region coal
                        block_counts[reg1] -= 1
                        regions3.append(reg1)
                        i += 1
                        j += 1
                    elif reg2 is None or (reg1 and reg1[0] < reg2[0]):
                        if block_counts[reg1] > 1:
                            regions3.append(reg1)
                        i += 1
                    else:
                        assert reg2, reg2
                        if block_counts[reg2] > 1:
                            regions3.append(reg2)
                        j += 1

                node.data["ancestral"] = regions3

            elif node.event == "recomb":
                # inherit all ancestral
                assert len(node.children) == 1, node
                node.data["ancestral"] = [
                    reg for reg in self.get_ancestral(
                    node.children[0], parent=node)
                    if block_counts[reg] > 1]

            else:
                raise Exception("unknown event '%s'" % node.event)

                    
    def get_ancestral(self, node, side=None, parent=None):
        """
        Get the ancestral sequence from an edge above a node 
        
        node -- node to get ancestral sequence from
        side -- 0 for left parent edge, 1 for right parental edge
        parent -- if given, determine side from parent node
        """

        # set side from parent
        if parent:
            side = node.parents.index(parent)

        if node.event == "recomb":
            if (parent and len(node.parents) == 2 and
                node.parents[0] == node.parents[1]):
                # special case where both children of a coal node are the same
                # recomb node.
                return node.data["ancestral"]
            
            regions = []
            for reg in node.data["ancestral"]:
                if side == 0:
                    if reg[1] <= node.pos:
                        # keep all regions fully left of recomb position
                        regions.append(reg)
                    elif reg[0] < node.pos:
                        # cut region
                        regions.append((reg[0], node.pos))
                elif side == 1:
                    if reg[0] >= node.pos:
                        # keep all regions fully right of recomb position
                        regions.append(reg)
                    elif reg[1] > node.pos:
                        # cut region
                        regions.append((node.pos, reg[1]))
                else:
                    raise Exception("side not specified")
            return regions
        
        elif node.event == "gene" or node.event == "coal":
            return node.data["ancestral"]

        else:
            raise Exception("unknown event '%s'" % node.event)

                            
                
    def get_marginal_tree(self, pos):
        """
        Returns the marginal tree of the ARG containing position 'pos'
        """

        # make new ARG to contain marginal tree
        tree = ARG()

        # populate tree with marginal nodes
        for node in self.postorder_marginal_tree(pos):
            tree.add(node.copy())
        
        # set parent and children
        for node2 in tree:
            node = self[node2.name]
            parent = self.get_local_parent(node, pos)
            if parent is not None and parent.name in tree.nodes:
                parent2 = tree[parent.name]
                node2.parents = [parent2]
                parent2.children.append(node2)
            else:
                tree.root = node2

        assert tree.root is not None, tree.nodes
        
        return tree


    def postorder_marginal_tree(self, pos):
        """
        Iterate postorder over the nodes in the marginal tree at position 'pos'
        """

        # initialize heap
        heap = [(node.age, node) for node in self.leaves()]
        seen = set([None])
        
        # add all ancestor of lineages
        while len(heap) > 0:
            age, node = heapq.heappop(heap)

            if "ancestral" in node.data:
                # if ancestral is set require ancestral seq present at pos
                for reg in node.data["ancestral"]:
                    if reg[0] < pos < reg[1]:
                        break
                else:
                    # terminate iteration, we are past the MRCA
                    return
            yield node

            # find correct marginal parent
            # add parent to lineages if it has not been seen before
            parent = self.get_local_parent(node, pos)
            
            if parent not in seen:
                heapq.heappush(heap, (parent.age, parent))
                seen.add(parent)


    def preorder_marginal_tree(self, pos, node=None):
        """
        Iterate postorder over the nodes in the marginal tree at position 'pos'
        """

        if node is None:
            node = arg.root

        # initialize heap
        heap = [node]
        
        # add all ancestor of lineages
        while len(heap) > 0:
            node = heap.pop()
            yield node

            for child in node.children:
                if self.get_local_parent(child, pos) == node:
                    heap.append(child)


    def get_local_parent(self, node, pos):
        """Return the local parent of 'node' for position 'pos'"""
        
        if (node.event == "gene" or node.event == "coal"):
            if len(node.parents) > 0:
                return node.parents[0]
            else:
                return None
        elif node.event == "recomb":
            return node.parents[0 if pos < node.pos else 1]
        else:
            raise Exception("unknown event '%s'" % node.event)
        
        
    def get_tree(self, pos=None):
        """
        Returns a treelib.Tree() object representing the ARG if it is a tree

        if 'pos' is given, return a treelib.Tree() for the marginal tree at
        position 'pos'.
        """

        # get marginal tree first
        if pos is not None:
            return self.get_marginal_tree(pos).get_tree()

        tree = treelib.Tree()

        # add all nodes
        for node in self:
            node2 = treelib.TreeNode(node.name)
            tree.add(node2)

        # set parent, children, dist
        for node in tree:
            node2 = self[node.name]
            node.parent = (tree[node2.parents[0].name]
                           if len(node2.parents) > 0 else None)
            node.children = [tree[c.name] for c in node2.children]

            if node.parent:
                node.dist = self[node.parent.name].age - node2.age

        tree.root = tree[self.root.name]
        return tree
            

    def prune(self, remove_single=True):
        """
        Prune ARG to only those nodes with ancestral sequence
        """

        # NOTE: be careful when removing nodes that you call get_ancestral
        # before changing parent/child orders
        
        # find pruned edges
        prune_edges = []
        for node in list(self):
            for parent in list(node.parents):
                if len(self.get_ancestral(node, parent=parent)) == 0:
                    prune_edges.append((node, parent))

        # remove pruneded edges
        for node, parent in prune_edges:
            parent.children.remove(node)
            node.parents.remove(parent)
        
        # remove pruned nodes
        for node in list(self):
            if len(node.data["ancestral"]) == 0:
                self.remove(node)


        for node in self:
            assert not node.is_leaf() or node.age == 0.0

        # remove single children
        if remove_single:
            remove_single_lineage(self)
            
        # set root
        # TODO: may need to actually use self.roots
        for node in list(self):
            if len(node.parents) == 0:
                dellist = []
                while len(node.children) == 1:
                    delnode = node
                    node = node.children[0]
                    self.remove(delnode)
                self.root = node
            

        

#=============================================================================
# coalescence with recombination

def sample_coal_recomb(k, n, r):
    """
    Returns a sample time for either coal or recombination

    k -- chromosomes
    n -- effective population size (haploid)
    r -- recombination rate (recombinations / chromosome / generation)

    Returns (event, time) where
    event -- 0 for coalesce event, 1 for recombination event
    time  -- time (in generations) of event
    """

    # coal rate = (k choose 2) / 2
    # recomb rate = k * r
    coal_rate = (k * (k-1) / 2) / n
    recomb_rate = k * r
    rate = coal_rate + recomb_rate

    event = ("coal", "recomb")[int(random.random() < (recomb_rate / rate))]
    
    return event, random.expovariate(rate)


def sample_coal_recomb_times(k, n, r, t=0):
    """
    Returns a sample time for either coal or recombination

    k -- chromosomes
    n -- effective population size (haploid)
    r -- recombination rate (recombinations / chromosome / generation)
    t -- initial time (default: 0)

    Returns (event, time) where
    event -- 0 for coalesce event, 1 for recombination event
    time  -- time (in generations) of event
    """

    times = []
    events = []

    while k > 1:
        event, t2 = sample_coal_recomb(k, n, r)
        t += t2
        times.append(t)
        events.append(event)
        if event == "coal":
            k -= 1
        elif event == "recomb":
            k += 1
        else:
            raise Exception("unknown event '%s'" % event)

    return times, events


def sample_arg(k, n, rho, start=0.0, end=0.0, t=0):

    arg = ARG(start, end)

    class Lineage (object):
        def __init__(self, node, regions, seqlen):
            self.node = node
            self.regions = regions
            self.seqlen = seqlen

    # init ancestral lineages
    # (node, region, seqlen)
    total_seqlen = k * (end - start)
    lineages = set(Lineage(arg.add(CoalNode(arg.new_name())),
                           [(start, end)], end-start)
                   for i in xrange(k))
    for lineage in lineages:
        lineage.node.data["ancestral"] = [(start, end)]
    recomb_parent_lineages = {}
    lineage_parents = {}

    # block start -> lineage count
    block_starts = [start]
    block_counts = {start: k}

    # perform coal, recomb
    while len(lineages) > 1:
        # sample time and event
        k = len(lineages)
        coal_rate = (k * (k-1) / 2) / n  # (k choose 2) / n
        recomb_rate = rho * total_seqlen
        rate = coal_rate + recomb_rate
        t2 = random.expovariate(rate)
        event = ("coal", "recomb")[int(random.random() < (recomb_rate / rate))]
        t += t2
        
        # process event
        if event == "coal":
            node = arg.add(CoalNode(arg.new_name(), age=t, event=event))

            # choose lineages to coal
            a, b = random.sample(lineages, 2)
            lineages.remove(a)
            lineages.remove(b)
            lineage_parents[a] = node
            lineage_parents[b] = node
            total_seqlen -= a.seqlen + b.seqlen

            # set parent, child links
            node.children = [a.node, b.node]
            a.node.parents.append(node)
            b.node.parents.append(node)

            # coal each non-overlapping region
            regions = []
            lineage_regions = []
            seqlen = 0
            nblocks = len(block_starts)
            i = 0
            
            for start, end, count in count_region_overlaps(
                a.regions, b.regions):                
                assert start != end, count in (0, 1, 2)
                #assert end == arg.end or end in block_starts
                i = block_starts.index(start, i)
                start2 = start
                while start2 < end:
                    end2 = block_starts[i+1] if i+1 < nblocks else arg.end

                    # region coalesces
                    if count == 2:
                        block_counts[start2] -= 1
                    if count >= 1:
                        regions.append((start2, end2)) # ancestral seq
                        if block_counts[start2] > 1:
                            # regions moves on, since not MRCA
                            lineage_regions.append((start2, end2))
                            seqlen += end2 - start2

                    # move to next region
                    i += 1
                    start2 = end2
            node.data["ancestral"] = regions

            # create 1 new lineage if any regions remain
            if len(lineage_regions) > 0:
                for reg in lineage_regions:
                    assert block_counts[reg[0]] > 1, (reg, block_counts)
                lineages.add(Lineage(node, lineage_regions, seqlen))
                total_seqlen += seqlen

            
        elif event == "recomb":
            node = arg.add(CoalNode(arg.new_name(), age=t, event=event))

            # choose lineage to recombine (weighted by seqlen)
            pick = random.random() * total_seqlen
            i = 0
            for lineage in lineages:
                i += lineage.seqlen
                if i >= pick:
                    break

            # set parent, child links
            lineage_parents[lineage] = node
            lineages.remove(lineage)
            node.children = [lineage.node]
            lineage.node.parents.append(node)
            node.data["ancestral"] = lineage.regions

            # choose recomb pos
            lens = [reg[1] - reg[0] for reg in lineage.regions]
            rstart, rend = lineage.regions[stats.sample(lens)]
            node.pos = rstart + random.random() * (rend - rstart)
            block_starts.append(node.pos)  # could be done faster
            block_starts.sort()            #
            prev_pos = block_starts[block_starts.index(node.pos)-1]
            block_counts[node.pos] = block_counts[prev_pos]

            # create 2 new lineages
            regions1 = list(split_regions(node.pos, 0, lineage.regions))
            regions2 = list(split_regions(node.pos, 1, lineage.regions))
            regions1_len = sum(reg[1] - reg[0] for reg in regions1)
            a = Lineage(node, regions1, regions1_len)
            b = Lineage(node, regions2, lineage.seqlen - regions1_len)
            lineages.add(a)
            lineages.add(b)
            recomb_parent_lineages[node] = (a, b)
        else:
            raise Exception("unknown event '%s'" % event)

    assert len(lineages) == 0, lineages

    # fix recomb parent order, so that left is before pos and right after
    for node, (a, b) in recomb_parent_lineages.iteritems():
        an = lineage_parents[a]
        bn = lineage_parents[b]
        for reg in a.regions: assert reg[1] <= node.pos
        for reg in b.regions: assert reg[0] >= node.pos
        node.parents = [an, bn]

    # TODO: set root(s)

    return arg
    

#=============================================================================
# arg functions


def lineages_over_time(k, events):
    """
    Computes number of lineage though time using coal/recomb events
    """

    for event in events:
        if event == "coal":
            k -= 1
        elif event == "recomb":
            k += 1
        else:
            raise Exception("unknown event '%s'" % event)        
        yield k
        

def make_arg_from_times(k, times, events):

    arg = ARG()

    # make leaves
    lineages  = set((arg.add(CoalNode(arg.new_name())), 1)
                     for i in xrange(k))

    # process events
    for t, event in izip(times, events):
        if event == "coal":
            node = arg.add(CoalNode(arg.new_name(), age=t, event=event))
            a, b = random.sample(lineages, 2)
            lineages.remove(a)
            lineages.remove(b)
            node.children = [a[0], b[0]]
            a[0].parents.append(node)
            b[0].parents.append(node)
            lineages.add((node, 1))
            
        elif event == "recomb":
            node = arg.add(CoalNode(arg.new_name(), age=t, event=event))
            a = random.sample(lineages, 1)[0]
            lineages.remove(a)
            node.children = [a[0]]
            a[0].parents.append(node)
            lineages.add((node, 1))
            lineages.add((node, 2))

        else:
            raise Exception("unknown event '%s'" % event)

    
    if len(lineages) == 1:
        arg.root = lineages.pop()[0]    

    return arg


def get_recomb_pos(arg):
    """
    Returns a sorted list of an ARG's recombination positions
    """
    rpos = [node.pos for node in
            arg if node.event == "recomb"]
    rpos.sort()
    return rpos


def iter_recomb_blocks(arg, start=None, end=None):
    """
    Iterates over the recombination blocks of an ARG
    """

    if start is None:
        start = arg.start
    if end is None:
        end = arg.end

    a = start
    b = start
    for pos in get_recomb_pos(arg):
        if pos < start:
            continue
        if pos > end:
            pos = end
            break
        b = pos
        yield (a, b)
        a = pos

    yield (a, end)


def iter_marginal_trees(arg, start=None, end=None):
    """
    Iterate over the marginal trees of an ARG
    """
    
    for a,b in iter_recomb_blocks(arg, start, end):
        yield arg.get_marginal_tree((a+b) / 2.0)
    

    
def descendants(node, nodes=None):
    """
    Return all descendants of a node in an ARG
    """
    if nodes is None:
        nodes = set()
    nodes.add(node)
    for child in node.children:
        if child not in nodes:
            descendants(child, nodes)
    return nodes


def remove_single_lineage(arg):
    """
    Remove unnecessary nodes with single parent and single child
    """
    for node in list(arg):
        if len(node.children) == 1 and len(node.parents) == 1:
            child = node.children[0]
            parent = node.parents[0]

            del arg.nodes[node.name]
            child.parents[child.parents.index(node)] = parent
            parent.children[parent.children.index(node)] = child


#=============================================================================
# region functions


def split_regions(pos, side, regions):
    """
    Iterates through the regions on the left (side=0) or right (side=1) of 'pos'
    """
    
    for reg in regions:
        if side == 0:
            if reg[1] <= pos:
                # keep all regions fully left of recomb position
                yield reg
            elif reg[0] < pos:
                # cut region
                yield (reg[0], pos)
        elif side == 1:
            if reg[0] >= pos:
                # keep all regions fully right of recomb position
                yield reg
            elif reg[1] > pos:
                # cut region
                yield (pos, reg[1])
        else:
            raise Exception("side not specified")


def count_region_overlaps(*region_sets):
    """
    Count how many regions overlap each interval (start, end)
    
    Iterates through (start, end, count) sorted
    """

    # build endpoints list
    end_points = []
    for regions in region_sets:
        for reg in regions:
            end_points.append((reg[0], 0))
            end_points.append((reg[1], 1))
    end_points.sort()

    count = 0
    start = None
    end = None
    last = None
    for pos, kind in end_points:
        if last is not None and pos != last:
            yield last, pos, count
        if kind == 0:
            count += 1
        elif kind == 1:
            count -= 1
        last = pos

    if last is not None and pos != last:
        yield last, pos, count
    

        
def groupby_overlaps(regions, bygroup=True):
    """
    Group ranges into overlapping groups
    Ranges must be sorted by start positions
    """

    start = -util.INF
    end = -util.INF
    group = None
    groupnum = -1
    for reg in regions:        
        if reg[0] > end:
            # start new group
            start, end = reg
            groupnum += 1

            if bygroup:
                if group is not None:
                    yield group
                group = [reg]
            else:
                yield (groupnum, reg)

        else:
            # append to current group
            if reg[1] > end:
                end = reg[1]

            if bygroup:
                group.append(reg)
            else:
                yield (groupnum, reg)

    if bygroup and group is not None and len(group) > 0:
        yield group


#=============================================================================
# mutations

def sample_mutations(arg, u):
    """
    u -- mutation rate (mutations/locus/gen)
    """

    mutations = []

    locsize = arg.end - arg.start

    for node in arg:
        for parent in node.parents:
            for region in arg.get_ancestral(node, parent=parent):
                frac = (region[1] - region[0]) / locsize
                dist = parent.age - node.age
                t = parent.age
                while True:
                    t -= random.expovariate(u * frac)
                    if t < node.age:
                        break
                    pos = random.uniform(region[0], region[1])
                    mutations.append((node, parent, pos, t))

    return mutations


def get_marginal_leaves(arg, node, pos):
    return (x for x in arg.preorder_marginal_tree(pos, node) if x.is_leaf())


#=============================================================================
# alignments

def make_alignment(arg, mutations, ancestral="A", derived="C"):
    aln = fasta.FastaDict()
    alnlen = int(arg.end - arg.start)
    leaves = list(arg.leaf_names())
    nleaves = len(leaves)

    # sort mutations by position
    mutations.sort(key=lambda x: x[2])

    # make align matrix
    mat = []
    
    pos = arg.start
    muti = 0
    for i in xrange(alnlen):
        if muti >= len(mutations) or i < int(mutations[muti][2]):
            # no mut
            mat.append(ancestral * nleaves)
        else:
            # mut
            node, parent, mpos, t = mutations[muti]
            row = []
            split = set(x.name for x in get_marginal_leaves(arg, node, mpos))
            mat.append("".join((derived if leaf in split else ancestral)
                               for leaf in leaves))
            muti += 1
    
    # make fasta
    for i, leaf in enumerate(leaves):
        aln[leaf] = "".join(x[i] for x in mat)

    return aln


#=============================================================================
# visualization

def layout_arg(arg, leaves=None, yfunc=lambda x: x):

    layout = {}

    if leaves is None:
        leaves = sorted((i for i in arg.leaves()), key=lambda x: x.name)

    # layout leaves
    leafx = util.list2lookup(leaves)
    
    for node in arg.postorder():
        if node.is_leaf():
            layout[node] = [leafx[node], yfunc(node.age)]
        else:
            layout[node] = [
                stats.mean(layout[child][0] for child in node.children),
                yfunc(node.age)]

    return layout


def show_arg(arg, layout=None, leaves=None, mut=None,
             recomb_width=.4, recomb_width_expand=0):
    from summon.core import lines, line_strip, zoom_clamp, color, hotspot
    from summon.shapes import box
    import summon

    win = summon.Window()
    
    if layout is None:
        layout = layout_arg(arg, leaves)

    def branch_hotspot(node, parent, x, y, y2):
        def func():
            print node.name, parent.name
        return hotspot("click", x-.5, y, x+.5, y2, func)

    for node in layout:
        recomb_width2 = recomb_width + node.age * recomb_width_expand
        
        if not node.is_leaf():
            x, y = layout[node]
            for i, child in enumerate(node.children):
                x2, y2 = layout[child]
                step = 0.0
                
                if child.event == "recomb":
                    if (len(child.parents) == 2 and
                        child.parents[0] == child.parents[1]):
                        step = recomb_width2 * [-1, 1][i]
                    else:
                        step = recomb_width2 * [-1, 1][
                            child.parents.index(node)]
                    win.add_group(line_strip(x, y,
                                             x2+step, y,
                                             x2+step, y2,
                                             x2, y2))                    
                else:
                    win.add_group(line_strip(x, y, x2, y, x2, y2))

                win.add_group(
                    branch_hotspot(child, node, x2+step, y, y2))

            # draw mutation
            if node.event == "recomb":
                win.add_group(zoom_clamp(
                    color(1, 0, 0),
                    box(x-.5, y-.5, x+.5, y+.5, fill=True),
                    color(1,1,1),
                    origin=(x, y),
                    minx=4.0, miny=4.0, maxx=20.0, maxy=20.0,
                    link=True))


    # draw mutations
    if mut:
        for node, parent, pos, t in mut:
            x, y = layout[parent]
            x2, y2 = layout[node]
            recomb_width2 = recomb_width + node.age * recomb_width_expand
            
            if node.event == "recomb":
                if (len(node.parents) == 2 and
                    node.parents[0] == node.parents[1]):
                    step = recomb_width2 * [-1, 1][i]
                else:
                    step = recomb_width2 * [-1, 1][node.parents.index(parent)]
            else:
                step = 0.0

            mx = x2+step
            my = t
            
            win.add_group(zoom_clamp(
                    color(0, 0, 1),
                    box(mx-.5, my-.5, mx+.5, my+.5, fill=True),
                    color(1,1,1),
                    origin=(mx, my),
                    minx=4.0, miny=4.0, maxx=20.0, maxy=20.0,
                    link=True))



    return win
    
    


def draw_tree(tree, layout, orient="vertical"):
    from summon.core import lines, line_strip, zoom_clamp, color, hotspot, \
         group
    import summon
    from summon.shapes import box
    
    vis = group()
    bends = {}

    for node in tree.postorder():
        # get node coordinates
        nx, ny = layout[node]
        px, py = layout[node.parents[0]] if node.parents else (nx, ny)

        # determine bend point
        if orient == "vertical":
            bends[node] = (nx, py)
        else:
            bends[node] = (px, ny)
        
        # draw branch
        vis.append(lines(nx, ny, bends[node][0], bends[node][1]))

        # draw cross bar
        if len(node.children) > 0:
            a = bends[node.children[-1]]
            b = bends[node.children[0]]
            vis.append(lines(a[0], a[1], b[0], b[1]))

    return vis


def draw_mark(x, y, col=(1,0,0), size=.5, func=None):
    from summon.core import zoom_clamp, color, group
    from summon.shapes import box

    if func:
        h = hotspot("click", x-size, y-size, x+size, y+size, func)
    else:
        h = group()
    
    return zoom_clamp(
        color(*col),
        box(x-size, y-size, x+size, y+size, fill=True),
        h,
        color(1,1,1),
        origin=(x, y),
        minx=4.0, miny=4.0, maxx=20.0, maxy=20.0,
        link=True)


