const { test } = require('node:test');
const assert = require('node:assert/strict');
const { cell, toTSV, roomSlugFromHeading } = require('../clipboard.js');
test('eight columns with blank optional D', () => assert.equal(toTSV(['url','name','raw','','speaker','00:01','text','https://example.org/room']), 'url\tname\traw\t\tspeaker\t00:01\ttext\thttps://example.org/room'));
test('embedded separators are flattened', () => assert.equal(cell('one\ttwo\r\nthree'), 'one two three'));
test('quotes are escaped for sheet TSV parsing', () => assert.equal(cell('He said "hi"'), '"He said ""hi"""'));
test('formula-like input is literal text', () => { for (const value of ['=1+1','+SUM(A1)','-1+2','@SUM(A1)',' \n=HYPERLINK("x")']) assert.ok(cell(value).includes("'")); });
test('empty and nonstring values', () => assert.equal(toTSV([null,undefined,'',0,false,'','','']), '\t\t\t0\tfalse\t\t\t'));
test('reject incorrect column counts', () => assert.throws(() => toTSV(['one'])));

test('heading room slug is explicit and unambiguous', () => {
  assert.equal(roomSlugFromHeading('Test (/demo-en-a)'), 'demo-en-a');
  assert.equal(roomSlugFromHeading('Test (/demo-en-a) (/demo-en-a)'), 'demo-en-a');
  for (const text of ['', 'room 123', '(/one) (/two)', '(/bad/path)', '(/bad?query)', '(//evil.example)', '(/bad_slug)']) assert.equal(roomSlugFromHeading(text), '');
});
