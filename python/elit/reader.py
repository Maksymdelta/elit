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
from elit.structure import *
import re
__author__ = 'Jinho D. Choi'

_TAB      = re.compile('\t')
_FEATS    = re.compile('\\|')
_FEATS_KV = re.compile(DELIM_FEAT_KV)
_ARC      = re.compile(DELIM_ARC)
_ARC_KV   = re.compile(DELIM_ARC_KV)


class TSVReader:
    """
    :param filename: the nament of a TSV file.
    :type  filename: str
    :param word_index: the column index of word forms.
    :type  word_index: int
    :param lemma_index: the column index of lemma.
    :type  lemma_index: int
    :param pos_index: the column index of part-of-speech tags.
    :type  pos_index: int
    :param feats_index: the column index of extra features.
    :type  feats_index: int
    :param head_id_index: the column index of primary head IDs.
    :type  head_id_index: int
    :param deprel_index: the column index of primary dependency labels.
    :type  deprel_index: int
    :param snd_heads_index: the column index of secondary dependency heads.
    :type  snd_heads_index: int
    :param nament_index: the column index of of named entity tags.
    :type  nament_index: int
    """

    def __init__(self, filename=None, word_index=-1, lemma_index=-1, pos_index=-1, feats_index=-1, head_id_index=-1,
                 deprel_index=-1, snd_heads_index=-1, nament_index=-1):
        if filename:
            self.fin = self.open(filename)

        self.word_index      = word_index
        self.lemma_index     = lemma_index
        self.pos_index       = pos_index
        self.feats_index     = feats_index
        self.head_id_index   = head_id_index
        self.deprel_index    = deprel_index
        self.snd_heads_index = snd_heads_index
        self.nament_index    = nament_index

    def __next__(self):
        graph = self.next()
        if graph: return graph
        else:     raise StopIteration

    def __iter__(self):
        return self

    def open(self, filename):
        """
        :param filename: the nament of a TSV file.
        :type  filename: str
        """
        self.fin = open(filename, buffering=200)
        return self.fin

    def close(self):
        self.fin.close()

    def next(self):
        tsv = []

        for line in self.fin:
            line = line.strip()
            if line:  tsv.append(_TAB.split(line))
            elif tsv: break

        return self.tsv_to_graph(tsv) if tsv else None

    def next_all(self):
        return [graph for graph in self]

    def tsv_to_graph(self, tsv):
        """
        :param tsv: each row represents a token, each column represents a field.
        :type  tsv: List[List[str]]
        """
        def get_field(row, index):
            return ROOT_TAG if row is None else row[index] if index >= 0 else None

        def get_feats(row):
            if self.feats_index >= 0:
                f = row[self.feats_index]
                if f == BLANK:
                    return None
                return {feat[0]: feat[1] for feat in map(_FEATS_KV.split, _FEATS.split(f))}
            return None

        def init_node(i):
            row = tsv[i]
            node = NLPNode()
            node.node_id = i + 1
            node.word    = get_field(row, self.word_index)
            node.lemma   = get_field(row, self.lemma_index)
            node.pos     = get_field(row, self.pos_index)
            node.nament  = get_field(row, self.nament_index)
            node.feats   = get_feats(row) if row else {}
            return node

        g = NLPGraph([init_node(i) for i in range(len(tsv))])

        if self.head_id_index >= 0:
            for i, n in enumerate(g):
                t = tsv[i]
                n.parent = NLPArc(g.nodes[int(t[self.head_id_index])], t[self.deprel_index])

                if self.snd_heads_index >= 0 and t[self.snd_heads_index] != BLANK:
                    for arc in map(_ARC_KV.split, _ARC.split(t[self.snd_heads_index])):
                        n.add_secondary_parent(NLPArc(g.nodes[int(arc[0])], arc[1]))

        return g