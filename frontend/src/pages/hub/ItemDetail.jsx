import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Alert, Button, Collapse, Descriptions, Empty, Modal, Spin, Tabs, Tag, Tooltip, Typography, message } from 'antd'
import Grid, { VISIBILITY } from './Grid'
import { getItem, getItemCode } from './api'

const schemaCols = [
  { headerName: '이름', field: 'name' },
  { headerName: '타입', field: 'type' },
]
const paramCols = [...schemaCols, { headerName: '필수', field: 'required' }]
const usedByCols = [
  { headerName: '이름', field: 'name', flex: 2 },
  { headerName: 'family', field: 'family' },
  { headerName: '팀', field: 'team' },
]

function Section({ title, children }) {
  return (
    <>
      <Typography.Title level={5} style={{ marginTop: 24 }}>
        {title}
      </Typography.Title>
      {children}
    </>
  )
}

function CodeModal({ itemKey, open, onClose }) {
  const [code, setCode] = useState(null)

  useEffect(() => {
    if (!open) return
    getItemCode(itemKey)
      .then(setCode)
      .catch((e) => {
        message.error(e.message)
        onClose()
      })
  }, [open, itemKey])

  const tabs = (code?.files || []).map((f) => ({
    key: f.path,
    label: f.path,
    children: (
      <pre className="code-view">
        <code>{f.content}</code>
      </pre>
    ),
  }))

  return (
    <Modal title="코드" open={open} onCancel={onClose} footer={null} width={1000} destroyOnClose>
      {code ? <Tabs items={tabs} /> : <Spin />}
    </Modal>
  )
}

/** tool/skill 상세 내용. ItemDrawer와 ItemPage가 같이 쓴다. */
export default function ItemDetail({ itemKey }) {
  const navigate = useNavigate()
  const [item, setItem] = useState(null)
  const [error, setError] = useState(null)
  const [codeOpen, setCodeOpen] = useState(false)

  useEffect(() => {
    setItem(null)
    setError(null)
    getItem(itemKey).then(setItem).catch((e) => setError(e.message))
  }, [itemKey])

  if (error) return <Empty description={error} />
  if (!item) return <Spin />

  const { spec } = item

  return (
    <>
      {item.deprecated ? (
        <Alert
          type="warning"
          showIcon
          message={`폐기된 ${item.type}입니다.${item.replaced_by ? ` 대체: ${item.replaced_by}` : ''}`}
          style={{ marginBottom: 16 }}
        />
      ) : null}

      <Descriptions bordered size="small" column={1}>
        <Descriptions.Item label="이름">{item.name}</Descriptions.Item>
        <Descriptions.Item label="key">{item.key}</Descriptions.Item>
        <Descriptions.Item label="type">
          <Tag color={item.type === 'tool' ? 'blue' : 'green'}>{item.type}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="팀">{item.team}</Descriptions.Item>
        <Descriptions.Item label="owner">{item.owner}</Descriptions.Item>
        <Descriptions.Item label="설명">{item.description}</Descriptions.Item>
        <Descriptions.Item label="공개범위">{VISIBILITY[item.code_visibility]}</Descriptions.Item>
      </Descriptions>

      <div style={{ marginTop: 16 }}>
        <Tooltip title={item.can_view_code ? null : '원 개발자 허락 필요'}>
          <Button type="primary" disabled={!item.can_view_code} onClick={() => setCodeOpen(true)}>
            코드 보기
          </Button>
        </Tooltip>
      </div>

      {item.type === 'tool' ? (
        <>
          <Section title="Spec">
            <Descriptions size="small" column={1}>
              <Descriptions.Item label="data_source">
                <Tag color="blue">{spec.data_source}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="tables">
                {(spec.tables || []).map((t) => (
                  <Tag key={t}>{t}</Tag>
                ))}
              </Descriptions.Item>
            </Descriptions>
          </Section>
          <Section title="params">
            <Grid autoHeight rowData={spec.params || []} columnDefs={paramCols} />
          </Section>
          <Section title="output_schema">
            <Grid autoHeight rowData={spec.output_schema || []} columnDefs={schemaCols} />
          </Section>
        </>
      ) : (
        <>
          <Section title="Spec">
            output_type <Tag color="green">{spec.output_type}</Tag>
          </Section>
          <Section title="input_schema">
            <Grid autoHeight rowData={spec.input_schema || []} columnDefs={schemaCols} />
          </Section>
          {spec.prompt && (
            <Collapse style={{ marginTop: 16 }}>
              <Collapse.Panel header="prompt" key="prompt">
                <pre className="code-view">{spec.prompt}</pre>
              </Collapse.Panel>
            </Collapse>
          )}
        </>
      )}

      <Section title="사용 중인 workflow">
        <Grid
          autoHeight
          rowData={item.used_by}
          columnDefs={usedByCols}
          onRowClicked={(e) => navigate(`/hub/workflows/${e.data.key}`)}
        />
      </Section>

      <CodeModal itemKey={item.key} open={codeOpen} onClose={() => setCodeOpen(false)} />
    </>
  )
}
