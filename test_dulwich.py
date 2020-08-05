import dulwich
from dulwich import porcelain
r = porcelain.clone("https://github.com/tickelton/impost0r-demo", "impost0r-demo")
f = open('impost0r-demo/data', 'w')
f.write('fooooobar0')
f.close()
porcelain.add(r, './impost0r-demo/data')
r.do_commit(message=b'dulwich test', committer=b'alice <alice@foo.com>', author=b'alice <alice@foo.com>', commit_timestamp=1556659323)
r2 = porcelain.push('impost0r-demo', 'https://USERNAME:PASSWORD@github.com/tickelton/impost0r-demo', 'm
aster')

