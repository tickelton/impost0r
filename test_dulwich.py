import dulwich
from dulwich import porcelain
import time
from datetime import timezone
import calendar
r = porcelain.clone("https://github.com/tickelton/impost0r-demo", "impost0r-demo")
f = open('impost0r-demo/data', 'w')
f.write('fooooobar0')
f.close()
porcelain.add(r, './impost0r-demo/data')
commit_stamp = calendar.timegm(time.strptime('2010-08-06', '%Y-%m-%d'))
r.do_commit(message=b'dulwich test', committer=b'alice <alice@foo.com>', author=b'alice <alice@foo.com>', commit_timestamp=commit_stamp, commit_timezone=3600)
r2 = porcelain.push('impost0r-demo', 'https://USERNAME:PASSWORD@github.com/tickelton/impost0r-demo', 'master')

