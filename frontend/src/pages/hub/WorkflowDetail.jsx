import { useEffect, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { Alert, Button, Card, Col, Descriptions, Empty, Row, Space, Spin, Steps, Tag, Typography } from 'antd'
import CodeFlow from './CodeFlow'
import ItemDrawer from './ItemDrawer'
import { getWorkflow } from './api'
import './hub.css'

export default function WorkflowDetail() {
  const { key } = useParams()
  const [params, setParams] = useSearchParams()
  const [wf, setWf] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    setWf(null)
    setError(null)
    getWorkflow(key).then(setWf).catch((e) => setError(e.message))
  }, [key])

  if (error) return <Empty description={error} />
  if (!wf) return <Spin />

  // 선택 상태는 URL(?step=&node=)에 둔다
  const stepKey = params.get('step')
  const nodeKey = params.get('node')
  const stepIndex = wf.biz_steps.findIndex((s) => s.key === stepKey)
  const step = wf.biz_steps[stepIndex]
  const node = wf.code_nodes.find((n) => n.key === nodeKey)

  const select = (changes) => {
    const next = new URLSearchParams(params)
    Object.entries(changes).forEach(([k, v]) => (v ? next.set(k, v) : next.delete(k)))
    setParams(next)
  }

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      {wf.deprecated ? (
        <Alert
          type="warning"
          showIcon
          message="폐기된 workflow입니다."
          description={
            wf.replaced_by && (
              <>
                대체: <Link to={`/hub/workflows/${wf.replaced_by}`}>{wf.replaced_by}</Link>
              </>
            )
          }
        />
      ) : null}

      <Card>
        <Typography.Title level={4} style={{ marginTop: 0 }}>
          {wf.name}
        </Typography.Title>
        {wf.description && <Typography.Paragraph type="secondary">{wf.description}</Typography.Paragraph>}
        <Descriptions size="small" column={3}>
          <Descriptions.Item label="family">{wf.family}</Descriptions.Item>
          <Descriptions.Item label="팀">{wf.team}</Descriptions.Item>
          <Descriptions.Item label="owner">{wf.owner}</Descriptions.Item>
          <Descriptions.Item label="원본">
            {wf.derived_from ? <Link to={`/hub/workflows/${wf.derived_from}`}>{wf.derived_from}</Link> : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="같은 family" span={2}>
            {wf.siblings.length
              ? wf.siblings.map((s) => (
                  <Link key={s.key} to={`/hub/workflows/${s.key}`} style={{ marginRight: 12 }}>
                    {s.name}
                    {s.deprecated ? ' (폐기)' : ''}
                  </Link>
                ))
              : '-'}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Row gutter={16}>
        <Col span={8}>
          <Card
            title="업무 Workflow"
            extra={
              <Button size="small" disabled={!step} onClick={() => select({ step: null })}>
                전체 보기
              </Button>
            }
          >
            <Steps
              direction="vertical"
              current={stepIndex}
              onChange={(i) => select({ step: wf.biz_steps[i].key })}
              items={wf.biz_steps.map((s) => ({
                title: s.title,
                description: (
                  <>
                    {s.description}
                    <div>
                      <Tag style={{ marginTop: 4 }}>노드 {(s.code_nodes || []).length}개</Tag>
                    </div>
                  </>
                ),
              }))}
            />
          </Card>
        </Col>
        <Col span={16}>
          <Card title="Code Workflow" bodyStyle={{ padding: 0 }}>
            {/* 단계 선택 시 그 단계의 node만 그린다. key에 step을 넣어 fitView를 다시 맞춘다 */}
            <CodeFlow
              key={`${wf.key}-${stepKey}`}
              codeNodes={step ? wf.code_nodes.filter((n) => step.code_nodes?.includes(n.key)) : wf.code_nodes}
              codeEdges={
                step ? wf.code_edges.filter((e) => e.every((k) => step.code_nodes?.includes(k))) : wf.code_edges
              }
              steps={wf.biz_steps}
              highlighted={null}
              selectedKey={nodeKey}
              onNodeClick={(k) => select({ node: k })}
            />
          </Card>
        </Col>
      </Row>

      <ItemDrawer itemKey={node?.ref} type={node?.type} title={node?.name} onClose={() => select({ node: null })} />
    </Space>
  )
}
