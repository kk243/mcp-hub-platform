import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Card, Empty, Input, List, Segmented, Space, Tag, Typography, message } from 'antd'
import Grid, { TagsCell, VISIBILITY } from './Grid'
import { getItems, getWorkflows } from './api'
import './hub.css'

const status = { headerName: '상태', valueGetter: (p) => (p.data.deprecated ? '폐기' : '사용'), maxWidth: 100 }
const visibility = { headerName: '공개범위', valueGetter: (p) => VISIBILITY[p.data.code_visibility], maxWidth: 120 }

// 메뉴별 설정: 조회 API, 표 컬럼, 카드 본문
const KINDS = {
  workflows: {
    placeholder: '이름, 설명, 태그로 workflow 검색',
    load: (q) => getWorkflows({ q }),
    columns: [
      { headerName: '이름', field: 'name', flex: 2 },
      { headerName: 'family', field: 'family', sort: 'asc' },
      { headerName: '팀', field: 'team' },
      { headerName: 'owner', field: 'owner' },
      { headerName: '단계 수', field: 'step_count', maxWidth: 110 },
      { headerName: '태그', field: 'tags', cellRenderer: TagsCell, flex: 2 },
      { headerName: '원본', field: 'derived_from' },
      status,
    ],
    meta: (w) => (
      <>
        <Tag color="purple">{w.family}</Tag>
        {w.team} · 단계 {w.step_count}개{w.derived_from && ` · 원본 ${w.derived_from}`}
      </>
    ),
  },
  tools: {
    placeholder: '이름, 설명, 태그, 테이블명으로 tool 검색',
    load: (q) => getItems({ type: 'tool', q }),
    columns: [
      { headerName: '이름', field: 'name', flex: 2 },
      { headerName: 'data_source', valueGetter: (p) => p.data.spec.data_source, sort: 'asc' },
      { headerName: 'tables', valueGetter: (p) => (p.data.spec.tables || []).join(', '), flex: 2 },
      { headerName: '사용처 수', field: 'used_by_count', maxWidth: 110 },
      { headerName: '팀', field: 'team' },
      visibility,
      status,
    ],
    meta: (t) => (
      <>
        <Tag color="blue">{t.spec.data_source}</Tag>
        {t.team} · 사용처 {t.used_by_count}곳
        <div className="hub-card-sub">{(t.spec.tables || []).join(', ')}</div>
      </>
    ),
  },
  skills: {
    placeholder: '이름, 설명, 태그로 skill 검색',
    load: (q) => getItems({ type: 'skill', q }),
    columns: [
      { headerName: '이름', field: 'name', flex: 2 },
      { headerName: 'output_type', valueGetter: (p) => p.data.spec.output_type, sort: 'asc' },
      { headerName: '사용처 수', field: 'used_by_count', maxWidth: 110 },
      { headerName: '팀', field: 'team' },
      visibility,
      status,
    ],
    meta: (s) => (
      <>
        <Tag color="green">{s.spec.output_type}</Tag>
        {s.team} · 사용처 {s.used_by_count}곳
      </>
    ),
  },
}

function CardView({ rows, meta, onOpen }) {
  if (!rows.length) return <Empty description="데이터가 없습니다" />
  return (
    <List
      grid={{ gutter: 16, xs: 1, sm: 2, lg: 3, xxl: 4 }}
      dataSource={rows}
      renderItem={(row) => (
        <List.Item>
          <Card
            hoverable
            size="small"
            title={row.name}
            extra={row.deprecated ? <Tag>폐기</Tag> : null}
            className={row.deprecated ? 'row-deprecated' : undefined}
            onClick={() => onOpen(row.key)}
          >
            <Typography.Paragraph type="secondary" ellipsis={{ rows: 2 }} style={{ minHeight: 44 }}>
              {row.description}
            </Typography.Paragraph>
            <div>{meta(row)}</div>
            <div style={{ marginTop: 8 }}>
              <TagsCell value={row.tags} />
            </div>
          </Card>
        </List.Item>
      )}
    />
  )
}

/** kind: workflows | tools | skills. 메뉴마다 검색과 보기 방식이 따로 동작한다. */
export default function HubList({ kind }) {
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const q = params.get('q') || ''
  const view = params.get('view') || 'table'
  const [rows, setRows] = useState([])
  const config = KINDS[kind]

  useEffect(() => {
    config.load(q).then(setRows).catch((e) => message.error(e.message))
  }, [kind, q])

  const setParam = (name, value) => {
    const next = new URLSearchParams(params)
    value ? next.set(name, value) : next.delete(name)
    setParams(next)
  }
  const open = (key) => navigate(`/hub/${kind}/${key}`)

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Space style={{ width: '100%', justifyContent: 'space-between' }}>
        <Input.Search
          placeholder={config.placeholder}
          defaultValue={q}
          allowClear
          enterButton
          onSearch={(value) => setParam('q', value)}
          style={{ width: 480 }}
        />
        <Segmented
          value={view}
          onChange={(v) => setParam('view', v)}
          options={[
            { label: '표', value: 'table' },
            { label: '카드', value: 'card' },
          ]}
        />
      </Space>

      {view === 'card' ? (
        <CardView rows={rows} meta={config.meta} onOpen={open} />
      ) : (
        <Grid rowData={rows} columnDefs={config.columns} onRowClicked={(e) => open(e.data.key)} />
      )}
    </Space>
  )
}
