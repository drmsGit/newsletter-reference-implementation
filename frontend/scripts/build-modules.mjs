// Compiles the email blocks from MJML to the HTML templates the backend renders
// (ADR-131 addendum 2026-10-15; task-371).
//
//   npm run build:modules            write storage/modules/email/<block>.html
//   npm run build:modules -- --check fail if a committed .html is not what
//                                    the pinned MJML makes of its .mjml (CI)
//
// A source is a whole `<mjml>` document with an `mj-body`; the rest
// (`_attributes.mjml`, `_text_link.mjml`, `_column_content.mjml`) are partials
// pulled in with `mj-include` and are not compiled on their own. This script
// pastes the partials in itself before compiling, because MJML 5 drops a body
// fragment included inside a column and does not apply `mj-attributes` that
// arrive through an include. The Jinja
// placeholders pass through untouched: values as attribute text, conditionals
// inside `mj-raw`.
//
// Each block keeps only its body. Of the styles MJML puts in the head, the
// responsive column widths are what the blocks need from it; they are the same
// for every block, so they are collected once into `_mjml_head.html`, which the
// email document includes with `data-css-inline="keep"` so inlining keeps the
// media queries. Only `@media` and `.moz-text-html` rules are kept, because a
// kept style is also inlined: MJML's element resets (`p`, `img`, `table`)
// would land on every module's elements, and the Outlook-only
// `.mj-outlook-group-fix { width:100% !important }`, which MJML hides in an
// `[if mso]` comment, would pin every column to full width. Outlook lays the
// columns out with the `[if mso]` tables in the body instead. MJML's viewport
// meta comes along: without it a phone lays the email out 980px wide and the
// media queries never stack the columns.
import { readdir, readFile, writeFile } from 'node:fs/promises'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import mjml2html from 'mjml'

const DIR = join(dirname(fileURLToPath(import.meta.url)), '..', '..', 'storage', 'modules', 'email')
const HEAD = '_mjml_head.html'
const INCLUDE = /<mj-include path="\.\/([\w-]+\.mjml)"\s*\/>/g
const check = process.argv.includes('--check')

function generated(source) {
  return `{# Generated from ${source} by npm run build:modules (frontend/). Do not edit: edit the .mjml. #}\n`
}

function between(html, open, close) {
  const start = html.indexOf(open)
  const end = html.lastIndexOf(close)
  if (start < 0 || end < 0) throw new Error(`no ${open}…${close} in the compiled output`)
  return html.slice(start + open.length, end)
}

async function compile(file) {
  const source = await expand(await readFile(join(DIR, file), 'utf8'))
  const result = await mjml2html(source, { filePath: join(DIR, file), validationLevel: 'soft' })
  // Soft validation, because a Jinja placeholder is not a colour or a size MJML
  // would accept; anything else it reports is a real mistake in the source.
  const errors = (result.errors ?? []).filter((e) => !/\{\{/.test(e.message))
  if (errors.length) throw new Error(`${file}: ${errors.map((e) => e.formattedMessage ?? e.message).join('; ')}`)
  const html = result.html
  // The body, without MJML's wrapper div: that one says role="article" and
  // belongs once around the whole email, not around each block.
  const inner = between(html.slice(html.indexOf('<body')), '>', '</body>')
  const body = between(inner.slice(inner.indexOf('<div')), '>', '</div>').trim()
  const css = [...between(html, '<head>', '</head>').matchAll(/<style[^>]*>([\s\S]*?)<\/style>/g)].map((m) => m[1])
  const viewport = between(html, '<head>', '</head>').match(/<meta name="viewport"[^>]*>/)?.[0]
  if (!viewport) throw new Error(`${file}: MJML wrote no viewport meta`)
  return { body, statements: css.flatMap(statements), viewport }
}

/** The source with every `mj-include` replaced by the partial it names. */
async function expand(source, seen = []) {
  const parts = []
  let last = 0
  for (const match of source.matchAll(INCLUDE)) {
    if (seen.includes(match[1])) throw new Error(`${match[1]} includes itself`)
    parts.push(source.slice(last, match.index), await expand(await readFile(join(DIR, match[1]), 'utf8'), [...seen, match[1]]))
    last = match.index + match[0].length
  }
  return parts.join('') + source.slice(last)
}

/** The top-level CSS statements a block needs from the head (see above), so
 * the same rule from two blocks is kept once. */
function statements(css) {
  const found = []
  let depth = 0
  let start = 0
  for (let i = 0; i < css.length; i++) {
    if (css[i] === '{') depth++
    else if (css[i] === '}' && --depth === 0) {
      found.push(css.slice(start, i + 1).replace(/\s+/g, ' ').trim())
      start = i + 1
    } else if (css[i] === ';' && depth === 0) {
      found.push(css.slice(start, i + 1).trim())
      start = i + 1
    }
  }
  return found.filter((s) => s.startsWith('@media') || s.startsWith('.moz-text-html'))
}

const files = (await readdir(DIR)).filter((f) => f.endsWith('.mjml')).sort()
const outputs = new Map()
const headStyles = []
let viewport = ''
for (const file of files) {
  if (!(await readFile(join(DIR, file), 'utf8')).includes('<mj-body')) continue
  const { body, statements: found, viewport: meta } = await compile(file)
  viewport = meta
  outputs.set(file.replace(/\.mjml$/, '.html'), `${generated(file)}${body}\n`)
  for (const statement of found) if (!headStyles.includes(statement)) headStyles.push(statement)
}
outputs.set(
  HEAD,
  `${generated('every block')}${viewport}\n<style data-css-inline="keep">\n${headStyles.join('\n')}\n</style>\n`,
)

let stale = []
for (const [name, text] of outputs) {
  const path = join(DIR, name)
  if (check) {
    const committed = await readFile(path, 'utf8').catch(() => null)
    if (committed !== text) stale.push(name)
  } else {
    await writeFile(path, text)
  }
}
if (check && stale.length) {
  console.error(`Compiled email blocks are out of date: ${stale.join(', ')}. Run npm run build:modules in frontend/ and commit the result.`)
  process.exit(1)
}
console.log(check ? `${outputs.size} compiled blocks are current.` : `Wrote ${outputs.size} files to storage/modules/email.`)
