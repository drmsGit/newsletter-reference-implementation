import { useState, type KeyboardEvent } from 'react'
import { Link } from 'react-router'

import { useCategoryDetail, useCategoryGraph, type CategoryGraph as Graph } from '../api/resources'
import { figureColumns } from '../components/ContentFigures'
import DataTable, { type DataColumn } from '../components/DataTable'
import ScreenState from '../components/ScreenState'
import { CATEGORIES } from './Categories'

type Node = Graph['nodes'][number]
type Edge = Graph['edges'][number]

const WIDTH = 900
const HEIGHT = 620
const CENTRE = { x: WIDTH / 2, y: HEIGHT / 2 }

/**
 * Where each category sits on the drawing: the Jinja graph's layout, moved to
 * the client (task-359). Main categories on an inner circle, the rest on an
 * outer ellipse, each in name order. Size grows with how often its records
 * were picked and how much signal it carries.
 */
export function layout(nodes: Node[]): Map<number, { x: number; y: number; r: number }> {
  const place = new Map<number, { x: number; y: number; r: number }>()
  const ring = (group: Node[], rx: number, ry: number, offset: number) =>
    [...group]
      .sort((a, b) => a.name.localeCompare(b.name))
      .forEach((node, index) => {
        const angle = offset + (2 * Math.PI * index) / Math.max(group.length, 1)
        place.set(node.id, {
          x: Math.round(CENTRE.x + rx * Math.cos(angle)),
          y: Math.round(CENTRE.y + ry * Math.sin(angle)),
          r: 16 + Math.min(34, node.selected_count * 4 + Math.abs(node.total_delta) * 0.4),
        })
      })
  ring(nodes.filter((n) => n.type === 'main'), 150, 150, -Math.PI / 2)
  ring(nodes.filter((n) => n.type !== 'main'), 260, 230, -Math.PI / 2 + 0.3)
  return place
}

/** Up, down or flat, in words too: never conveyed by colour alone. */
function trend(node: Node): 'up' | 'down' | 'flat' {
  return node.avg_delta > 0 ? 'up' : node.avg_delta < 0 ? 'down' : 'flat'
}

function described(node: Node): string {
  return `${node.name}: ${node.content_count} records, picked ${node.selected_count} times, ` +
    `signal ${node.total_delta} (${trend(node) === 'up' ? 'rising' : trend(node) === 'down' ? 'falling' : 'none'})`
}

const COLUMNS: DataColumn<Node>[] = [
  { key: 'name', header: 'Category', isRowHeader: true, render: (n) => n.name },
  { key: 'records', header: 'Records', render: (n) => String(n.content_count) },
  { key: 'picked', header: 'Picked', render: (n) => String(n.selected_count) },
  { key: 'signal', header: 'Signal', render: (n) => String(n.total_delta) },
  { key: 'trend', header: 'Trend', render: (n) => ({ up: 'rising', down: 'falling', flat: '—' })[trend(n)] },
]

/**
 * The category graph (task-359): the detail view the monitoring overview
 * leaves out. Categories and how they connect — by a parent–child link
 * (dark) or by records they share (light) — sized by picks and signal, for
 * this brand's records and audience. Choosing one shows its records and how
 * each did.
 */
export default function CategoryGraph() {
  const graph = useCategoryGraph()
  const [selected, setSelected] = useState<number | null>(null)
  return (
    <>
      <h1>Category graph</h1>
      <p className="muted">
        Each circle is a category: bigger when its records were picked more often and its signal is stronger;
        green with ▲ when interest is rising, amber with ▼ when it is falling. A dark line is a parent–child link, a light one
        records the two share. Choose a category to see its records.
      </p>
      <ScreenState query={graph}>
        {graph.data && (
          <div className="graph-view">
            <Drawing graph={graph.data} selected={selected} onSelect={setSelected} />
            <aside className="graph-panel" aria-label="Selected category">
              {selected == null ? (
                <p className="muted">Choose a category in the drawing or the table.</p>
              ) : (
                <Panel id={selected} />
              )}
            </aside>
            <DataTable
              label="Categories in the graph"
              columns={COLUMNS}
              items={graph.data.nodes}
              emptyMessage="There are no categories yet."
              onRowAction={(n) => setSelected(n.id)}
            />
          </div>
        )}
      </ScreenState>
    </>
  )
}

function Drawing({ graph, selected, onSelect }: { graph: Graph; selected: number | null; onSelect: (id: number) => void }) {
  const place = layout(graph.nodes)
  const press = (id: number) => (event: KeyboardEvent) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      onSelect(id)
    }
  }
  const width = (edge: Edge) => 1 + Math.min(8, edge.strength + Math.abs(edge.total_delta) * 0.2)
  return (
    <svg className="graph-drawing" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="group" aria-label="Category graph">
      {graph.edges.map((edge) => {
        const a = place.get(edge.source)
        const b = place.get(edge.target)
        if (!a || !b) return null
        return (
          <line
            key={`${edge.source}-${edge.target}`}
            x1={a.x} y1={a.y} x2={b.x} y2={b.y}
            className={`graph-edge graph-edge--${edge.type}`}
            strokeWidth={width(edge)}
          />
        )
      })}
      {graph.nodes.map((node) => {
        const at = place.get(node.id)!
        return (
          <g
            key={node.id}
            role="button"
            tabIndex={0}
            aria-label={described(node)}
            aria-pressed={selected === node.id}
            className={`graph-node graph-node--${trend(node)}${selected === node.id ? ' graph-node--selected' : ''}`}
            onClick={() => onSelect(node.id)}
            onKeyDown={press(node.id)}
          >
            <title>{described(node)}</title>
            <circle cx={at.x} cy={at.y} r={at.r} />
            <text x={at.x} y={at.y + at.r + 14} textAnchor="middle">
              {node.name}
              {/* The trend for the eye, beside its colour (task-392 item 1); the
                  button's name already says it in words. */}
              {trend(node) !== 'flat' && <tspan aria-hidden="true">{trend(node) === 'up' ? ' ▲' : ' ▼'}</tspan>}
            </text>
          </g>
        )
      })}
    </svg>
  )
}

function Panel({ id }: { id: number }) {
  const detail = useCategoryDetail(id)
  const data = detail.data
  const records = (data?.assigned_content ?? []).map((r) => ({ ...r, id: r.content_id }))
  type Row = (typeof records)[number]
  const columns: DataColumn<Row>[] = [
    { key: 'title', header: 'Record', isRowHeader: true, render: (r) => <Link to={`/content/${r.content_id}`}>{r.title}</Link> },
    ...figureColumns<Row>((r) => r.figures),
  ]
  return (
    <ScreenState query={detail}>
      {data && (
        <>
          <h2>{data.category.name}</h2>
          <p>
            <Link to={`${CATEGORIES}/${id}`}>The category's page</Link>
          </p>
          <dl className="facts">
            <dt>Under</dt>
            <dd>{data.parents.map((p) => p.name).join(', ') || '—'}</dd>
            <dt>Subcategories</dt>
            <dd>{data.children.map((c) => c.name).join(', ') || '—'}</dd>
            <dt>Signal</dt>
            <dd>
              {data.impact.total_delta} over {data.impact.update_count} updates
            </dd>
          </dl>
          <DataTable label={`Records in ${data.category.name}`} columns={columns} items={records}
            emptyMessage="No record of this brand is in this category." />
        </>
      )}
    </ScreenState>
  )
}
