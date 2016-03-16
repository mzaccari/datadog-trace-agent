
from collections import namedtuple
from itertools import tee, izip, chain, groupby
import math
import numpy as np


class Entry(object):

    def __init__(self, v, g, d):
        self.v = v
        self.g = g
        self.d = d

    def __repr__(self):
        return "v:%s g:%s d:%s" % (self.v, self.g, self.d)


class Summary(object):

    def __init__(self):
        self.entries = []
        self.epsilon = 0.01
        self.count = 0

    def sample(self, v):
        if self.count % (1 / self.epsilon * 2) == 0:
            self._compress()

        e = Entry(v, 1, 0)
        i = 0
        while i < len(self.entries):
            if self.entries[i].v > v:
                break
            i += 1

        if 0 < i < len(self.entries)-1:
            eprime = self.entries[i]
            e.d = eprime.g + eprime.d - 1

        self.entries.insert(i, e)
        self.count += 1
        self._validate()

    def _compress(self):
        err_thresh = int(self.epsilon * 2 * self.count)
        i = len(self.entries) - 1
        start_length = len(self.entries)
        while i > 1:
            e = self.entries[i]
            g = e.g
            j = i - 1
            while j > 0:
                eprime = self.entries[j]
                if (g + eprime.g + e.d > err_thresh):
                    break # err too big!
                g += eprime.g
                j -= 1

            j += 1

            if j < i:
                e.g = g
                self.entries[i] = e
                self.entries = self.entries[:j] + self.entries[i:]
                self._validate()

            i = j - 1

        # print 'start:%s end:%s' % (start_length, len(self.entries))

    def _capacity(self, i):
        e = self.entries[i]
        n = len(self.entries)
        g = e.v
        d = e.d

        p = int(2*self.epsilon*n)
        threshold = math.ceil(math.log(2*self.epsilon*2)/math.log(2))
        if d == 0:
            return threshold +1
        elif d == p:
            return 0

        e1 = 0
        e2 = 1
        for e1, e2 in pairwise(range(threshold)):
            t1 = 2**e1
            t2 = 2**e2

            lower = p - t2 - (p % t1)
            upper = p - t1 - (p % t1)
            if lower < d <= upper:
                break

        return e2

    def quant(self, q):
        if not self.entries:
            return None

        if q <= 0:
            return self.entries[0].v
        elif q >= 1:
            return self.entries[-1].v

        thresh = int(q * float(self.count)) + self.epsilon*self.count
        min_rank = 0
        for e1, e2 in pairwise(self.entries):
            min_rank += e1.g
            if min_rank + e2.g + e2.d > thresh:
                return e1.v

        return self.entries[-1].v

    @classmethod
    def merge(cls, s1, s2):
        s = cls()
        s.entries = s1.entries + s2.entries
        s.entries.sort(key=lambda e:e.v)
        s.count = s1.count + s2.count
        s._compress()
        return s

    def _validate(self):
        total = 0
        last = None
        for e in self.entries:
            if last is not None:
                assert e.v >= last.v, '%s !!! %s' %  (last, e)
            total += e.g
            last = e

        assert total == self.count, "%s != %s" % (total, self.count)


def pairwise(iterable):
    """ Return the elements of iterable in pairs.
        s -> (s0,s1), (s1,s2), (s2, s3), ...a
    """
    a, b = tee(iterable)
    next(b, None)
    return izip(a, b)



if __name__ == '__main__':

    inputs = np.random.rand(2000)

    # merged
    s1 = Summary()
    s2 = Summary()
    for i in inputs:
        s1.sample(i)
        s2.sample(i)
    s3 = Summary.merge(s1, s2)

    # not merged
    s4 = Summary()
    for loops in range(2):
        for i in inputs:
            s4.sample(i)

    for q in range(0, 110, 10):
        exact = np.percentile(inputs, q)
        m = s3.quant(q/100.0)
        n = s4.quant(q/100.0)
        print 'q:%2s exact:%.3f merged:%.3f not-merged:%.3f' % (q, exact, m, n)



