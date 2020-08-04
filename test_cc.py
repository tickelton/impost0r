import os
import sys
import pygit2
import stat
from time import time


data = 'This is an empty README file'
fn = 'README'

s = pygit2.Signature('Alice Author', 'alice@authors.tld', int(time()), 0)

r = pygit2.init_repository('foo', False)
bld = r.TreeBuilder()
t = bld.write()
c = r.create_commit('HEAD', s,s, 'Create master branch', t, [])


f = open(os.path.join(r.workdir,fn), 'w')
f.write(data)
f.close()

b = r.create_blob_fromworkdir(fn)
bld = r.TreeBuilder()
bld.insert(fn, b, os.stat(os.path.join('foo', fn)).st_mode )
t = bld.write()

r.index.read()
r.index.add(fn)
r.index.write()


c = r.create_commit('HEAD', s,s, 'Added a README', t, [r.head.target])
