# ========================================================================
# Copyright 2017 Emory University
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========================================================================
import functools
from enum import Enum
from typing import Dict
from typing import List
from typing import Union
from itertools import islice
from elit.util.bisect import bisect_left
from elit.util.bisect import bisect_right
from elit.util.bisect import bisect_index
from elit.util.bisect import bisect_remove
from elit.util.bisect import insort_right

__author__ = 'Jinho D. Choi'

# fields
BLANK = '_'
ROOT_TAG = '@#r$%'

# delimiters
DELIM_FEAT    = '|'
DELIM_FEAT_KV = '='
DELIM_ARC     = ';'
DELIM_ARC_KV  = ':'


@functools.total_ordering
class NLPNode:
    """
    :param node_id: node id.
    :param word: word form.
    :param lemma: lemma.
    :param pos: part-of-speech tag.
    :param nament: named entity tag.
    :param feats: extra features.
    """
    def __init__(self, node_id: int=-1, word: str=None, lemma: str=None, pos: str=None, nament: str=None,
                 feats: Dict[str, str]=None):
        # fields
        self.node_id: int = node_id
        self.word: str = word
        self.lemma: str = lemma
        self.pos: str = pos
        self.nament: str = nament
        self.feats: Dict[str, str] = feats or {}

        # dependencies
        self.parent: NLPNode = None
        self.children: List[NLPNode] = []
        self.secondary_parents: List[NLPNode] = []
        self.secondary_children: List[NLPNode] = []
        self.deprels: Dict[NLPNode, str] = {}

    def __hash__(self):
        return hash(id(self))

    def __lt__(self, other):
        return self.node_id < other.node_id

    def __eq__(self, other):
        return id(self) == id(other)

    def __str__(self):
        node_id = str(self.node_id)
        word    = self.word if self.word else BLANK
        lemma   = self.lemma if self.lemma else BLANK
        pos     = self.pos if self.pos else BLANK
        nament  = self.nament if self.nament else BLANK
        feats   = DELIM_FEAT.join((DELIM_FEAT_KV.join((k, v)) for k, v in self.feats.items())) if self.feats else BLANK
        head_id = str(self.parent.node_id) if self.parent else BLANK
        deprel  = self.get_dependency_label(self.parent) or BLANK
        sheads  = DELIM_ARC.join(DELIM_ARC_KV.join((str(parent.node_id), self.get_dependency_label(parent)))
                                 for parent in self.secondary_parents) if self.secondary_parents else BLANK
        return '\t'.join((node_id, word, lemma, pos, feats, head_id, deprel, sheads, nament))

    def set_pos(self, pos: str) -> str:
        """
        :param pos: the part-of-speech tag to be assigned to this node.
        :return: the previous part-of-speech tag if exists; otherwise, None.
        """
        self.pos, prev = pos, self.pos
        return prev

    @classmethod
    def root(cls):
        return cls(node_id=0, word=ROOT_TAG, lemma=ROOT_TAG, pos=ROOT_TAG, nament=ROOT_TAG)

    @property
    def grandparent(self) -> 'NLPNode':
        """
        :return: the GRANDPARENT of this node if exists; otherwise, None.
        """
        return self.parent.parent if self.parent else None

    def get_dependency_label(self, node: 'NLPNode'=None) -> str:
        """
        :param node: the parent of this node.
        :return: the dependency label between this node and the PARENT node if exists; otherwise, None.
        """
        if node is None: node = self.parent
        return self.deprels.get(node, None) if node else None

    def set_dependency_label(self, node: 'NLPNode', label: str):
        """
        :param node: the PARENT of this node.
        :param label: the dependency relation to the PARENT.
        """
        if label: self.deprels[node] = label

    def set_parent(self, node: 'NLPNode', label: str=None) -> 'NLPNode':
        """
        :param node: the node to be set as the PARENT of this node.
        :param label: the dependency relation between this node and the PARENT.
        :return the previous PARENT if exists; otherwise, None.
        """
        # handle the previous PARENT
        prev_parent = self.parent

        if prev_parent:
            bisect_remove(prev_parent.children, self)
            del self.deprels[prev_parent]

        # set the current PARENT
        self.parent = node

        if node:
            insort_right(node.children, self)
            self.set_dependency_label(node, label)

        return prev_parent

    def child_of(self, node: 'NLPNode') -> bool:
        """
        :param node: the node to be compared.
        :return: True if this node is a child of the specific node; otherwise, False.
        """
        return self.parent and self.parent == node

    def add_secondary_parent(self, node: 'NLPNode', label: str=None):
        """
        :param node: the node to be added as a secondary PARENT.
        :param label: the dependency relation to the PARENT.
        """
        insort_right(self.secondary_parents, node)
        insort_right(node.secondary_children, self)
        self.set_dependency_label(node, label)

    def remove_secondary_parent(self, node: 'NLPNode') -> bool:
        """
        :param node: the node to be removed from the secondary PARENT list.
        :return: True if the node is removed successfully; otherwise, False.
        """
        idx = bisect_index(self.secondary_parents, node)
        if idx >= 0:
            del self.secondary_parents[idx]
            self.deprels.pop(node, None)
            return True
        return False

    def get_leftmost_child(self, order: int=0) -> Union['NLPNode', None]:
        """
        :param order: order displacement (0: leftmost, 1: 2nd leftmost, etc.).
        :return: the leftmost child whose token position is on the left-hand side of this node if exists;
                 otherwise, None.
        """
        idx = order
        return self.children[idx] if 0 <= idx < len(self.children) and self.children[idx] < self else None

    def get_rightmost_child(self, order: int=0) -> Union['NLPNode', None]:
        """
        :param order: order displacement (0: rightmost, 1: 2nd rightmost, etc.).
        :return: the rightmost child whose token position is on the right-hand side of this node if exists;
                 otherwise, None.
        """
        idx = len(self.children) - 1 - order
        return self.children[idx] if 0 <= idx < len(self.children) and self.children[idx] > self else None

    def get_left_nearest_child(self, order: int=0) -> Union['NLPNode', None]:
        """
        :param order: order displacement (0: left-nearest, 1: 2nd left-nearest, etc.).
        :return: the left-nearest child whose token position is on the left-hand side of this node if exists;
                 otherwise, None.
        """
        idx = bisect_left(self.children, self) - 1 - order
        return self.children[idx] if 0 <= idx < len(self.children) else None

    def get_right_nearest_child(self, order: int=0) -> Union['NLPNode', None]:
        """
        :param order: order displacement (0: right-nearest, 1: 2nd right-nearest, etc.).
        :return: the right-nearest primary child whose token position is on the right-hand side of this node
                 if exists; otherwise, None.
        """
        idx = bisect_right(self.children, self) + order
        return self.children[idx] if 0 <= idx < len(self.children) else None

    def get_leftmost_sibling(self, order: int=0) -> Union['NLPNode', None]:
        """
        :param order: order displacement (0: leftmost, 1: 2nd leftmost, etc.).
        :return: the leftmost primary sibling whose token position is on the left-hand side of this node if exists;
                 otherwise, None.
        """
        idx = order
        return self.parent.children[idx] \
            if self.parent and 0 <= idx < len(self.parent.children) and self.parent.children[idx] < self else None

    def get_rightmost_sibling(self, order: int=0) -> Union['NLPNode', None]:
        """
        :param order: order displacement (0: rightmost, 1: 2nd rightmost, etc.).
        :return: the rightmost primary sibling whose token position is on the right-hand side of this node if exists;
                 otherwise, None.
        """
        idx = len(self.children) - 1 - order
        return self.parent.children[idx] \
            if self.parent and 0 <= idx < len(self.parent.children) and self.parent.children[idx] > self else None

    def get_left_nearest_sibling(self, order: int=0) -> Union['NLPNode', None]:
        """
        :param order: order displacement (0: left-nearest, 1: 2nd left-nearest, etc.).
        :return: the left-nearest primary sibling whose token position is on the left-hand side of this node if exists;
                 otherwise, None.
        """
        if self.parent:
            idx = bisect_left(self.parent.children, self) - 1 - order
            return self.parent.children[idx] if 0 <= idx < len(self.parent.children) else None
        return None

    def get_right_nearest_sibling(self, order: int=0) -> Union['NLPNode', None]:
        """
        :param order: order displacement (0: right-nearest, 1: 2nd right-nearest, etc.).
        :return: the right-nearest primary sibling whose token position is on the right-hand side of this node
                 if exists; otherwise, None.
        """
        if self.parent:
            idx = bisect_right(self.parent.children, self) + 1 + order
            return self.parent.children[idx] if 0 <= idx < len(self.parent.children) else None
        return None


class NLPGraph:
    """
    :param nodes: a list of NLP nodes whose parents are not initialized.
    :type  nodes: List[NLPNode]
      An artificial root is automatically added to the front of the node list.
    """
    def __init__(self, nodes: List[NLPNode]=None):
        self.nodes = [NLPNode.root()]
        if nodes: self.nodes.extend(nodes)

    def __next__(self):
        try: return next(self._iter)
        except StopIteration: raise StopIteration

    def __iter__(self):
        self._iter = islice(self.nodes, 1, len(self.nodes))
        return self

    def __str__(self):
        return '\n'.join(map(str, self))

    def __len__(self):
        return len(self.nodes) - 1


class Relation(Enum):
    PARENT                    = 'p'
    LEFTMOST_CHILD            = 'lmc'
    RIGHTMOST_CHILD           = 'rmc'
    LEFT_NEAREST_CHILD        = 'lnc'
    RIGHT_NEAREST_CHILD       = 'rnc'
    LEFTMOST_SIBLING          = 'lms'
    RIGHTMOST_SIBLING         = 'rms'
    LEFT_NEAREST_SIBLING      = 'lns'
    RIGHT_NEAREST_SIBLING     = 'rns'

    GRANDPARENT               = 'gp'
    SND_LEFTMOST_CHILD        = 'lmc2'
    SND_RIGHTMOST_CHILD       = 'rmc2'
    SND_LEFT_NEAREST_CHILD    = 'lnc2'
    SND_RIGHT_NEAREST_CHILD   = 'rnc2'
    SND_LEFTMOST_SIBLING      = 'lms2'
    SND_RIGHTMOST_SIBLING     = 'rms2'
    SND_LEFT_NEAREST_SIBLING  = 'lns2'
    SND_RIGHT_NEAREST_SIBLING = 'rns2'