const fs = require('fs');
const html = fs.readFileSync(process.argv[2], 'utf8').replace(/\r\n/g, '\n');
const re = /<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/gi;
let m, n = 0, bad = 0;
while ((m = re.exec(html)) !== null) {
  n++;
  try { new Function(m[1]); } catch (e) {
    bad++;
    const line = html.slice(0, m.index).split('\n').length;
    console.log(`SYNTAX ERROR in <script> #${n} starting at line ${line}: ${e.message}`);
  }
}
console.log(`checked ${n} inline script blocks, ${bad} with syntax errors`);
if (bad) process.exitCode = 1;
if (typeof _toXdsTemplate === 'undefined') {
  // pull the helper out and unit test it
  const src = html.match(/function _toXdsTemplate\(path\) \{[\s\S]*?\n        \}\n/)[0];
  const f = new Function(src + '; return _toXdsTemplate;')();
  for (const p of ['/data/frame_0001.cbf', '/data/lyso_1_master.h5', '/data/lyso_1_data_000003.h5',
                   'C:\\data\\run7_master.h5', '/data/foo_000001.h5', '/data/lyso_1_??????.h5', '/data/weird.h5'])
    console.log('  ', p, '->', f(p));
}
