import { useState } from 'react'
import { Alert, Button, Card, Form, Input, Modal, Radio, Select, Space, Tabs, Tag, Upload, message } from 'antd'
import Grid from './Grid'
import { deprecate, getItem, getWorkflow, importZip, setVisibility, updateMeta } from './api'
import './hub.css'

const createdCols = [
  { headerName: '종류', field: 'kind', maxWidth: 120 },
  { headerName: 'key', field: 'key', flex: 2 },
  { headerName: '이름', field: 'name', flex: 2 },
  { headerName: '상태', field: 'status', maxWidth: 120 },
]

function MessageList({ type, title, list }) {
  if (!list.length) return null
  return (
    <Alert
      type={type}
      showIcon
      message={`${title} ${list.length}건`}
      description={
        <ul style={{ margin: 0, paddingLeft: 20 }}>
          {list.map((m) => (
            <li key={m}>{m}</li>
          ))}
        </ul>
      }
    />
  )
}

function UploadTab() {
  const [file, setFile] = useState(null)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  const run = async (dryRun) => {
    setLoading(true)
    try {
      const res = await importZip(file, dryRun)
      setResult(res)
      if (!dryRun && !res.errors.length) {
        message.success('등록했습니다')
        setFile(null)
      }
    } catch (e) {
      message.error(e.message)
    } finally {
      setLoading(false)
    }
  }

  const confirmImport = () =>
    Modal.confirm({
      title: '등록할까요?',
      content: `${file.name}의 workflow와 신규 tool/skill이 등록됩니다. 등록 후 로직은 수정할 수 없습니다.`,
      okText: '등록',
      cancelText: '취소',
      onOk: () => run(false),
    })

  const canImport = file && result && !result.errors.length

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Upload.Dragger
        accept=".zip"
        fileList={file ? [file] : []}
        beforeUpload={(f) => {
          setFile(f)
          setResult(null)
          return false
        }}
        onRemove={() => {
          setFile(null)
          setResult(null)
        }}
      >
        <p className="ant-upload-text">등록 패키지(zip)를 끌어놓거나 클릭해서 선택하세요</p>
      </Upload.Dragger>

      <Space>
        <Button disabled={!file} loading={loading} onClick={() => run(true)}>
          검증
        </Button>
        <Button type="primary" disabled={!canImport} loading={loading} onClick={confirmImport}>
          등록
        </Button>
      </Space>

      {result && (
        <>
          {!result.errors.length && <Alert type="success" showIcon message="에러가 없습니다" />}
          <MessageList type="error" title="에러" list={result.errors} />
          <MessageList type="warning" title="경고" list={result.warnings} />
          <Grid autoHeight rowData={result.created} columnDefs={createdCols} />
        </>
      )}
    </Space>
  )
}

function EditTab() {
  const [form] = Form.useForm()
  const [target, setTarget] = useState('workflow')
  const [record, setRecord] = useState(null)
  const [deprecateOpen, setDeprecateOpen] = useState(false)
  const [replacedBy, setReplacedBy] = useState('')
  const [visibility, setVis] = useState({ code_visibility: 'private', allowlist: [] })

  const load = async (key) => {
    if (!key) return
    try {
      const data = target === 'workflow' ? await getWorkflow(key) : await getItem(key)
      setRecord(data)
      form.setFieldsValue(data)
      setVis({ code_visibility: data.code_visibility, allowlist: data.allowlist })
    } catch (e) {
      setRecord(null)
      message.error(e.message)
    }
  }

  const action = async (fn, okMessage) => {
    try {
      await fn()
      message.success(okMessage)
      load(record.key)
    } catch (e) {
      message.error(e.message)
    }
  }

  const save = (fields) => action(() => updateMeta(target, record.key, fields), '저장했습니다')

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%', maxWidth: 720 }}>
      <Space>
        <Select
          value={target}
          onChange={(v) => {
            setTarget(v)
            setRecord(null)
          }}
          options={[
            { value: 'workflow', label: 'Workflow' },
            { value: 'item', label: 'Tool / Skill' },
          ]}
          style={{ width: 140 }}
        />
        <Input.Search placeholder="key 입력" enterButton="불러오기" onSearch={load} style={{ width: 400 }} />
      </Space>

      {record && (
        <>
          <Card
            title={
              <>
                {record.key} {record.deprecated ? <Tag color="red">폐기됨</Tag> : null}
              </>
            }
            extra={
              <Button danger disabled={!!record.deprecated} onClick={() => setDeprecateOpen(true)}>
                폐기
              </Button>
            }
          >
            <Form form={form} layout="vertical" onFinish={save}>
              <Form.Item name="name" label="이름" rules={[{ required: true }]}>
                <Input />
              </Form.Item>
              <Form.Item name="description" label="설명">
                <Input.TextArea rows={3} />
              </Form.Item>
              <Form.Item name="tags" label="태그">
                <Select mode="tags" open={false} />
              </Form.Item>
              <Form.Item name="team" label="팀">
                <Input />
              </Form.Item>
              <Form.Item name="owner" label="owner">
                <Input />
              </Form.Item>
              <Button type="primary" htmlType="submit">
                저장
              </Button>
            </Form>
          </Card>

          {target === 'item' && (
            <Card title="코드 공개범위">
              <Space direction="vertical" style={{ width: '100%' }}>
                <Radio.Group
                  value={visibility.code_visibility}
                  onChange={(e) => setVis({ ...visibility, code_visibility: e.target.value })}
                >
                  <Radio value="public">public</Radio>
                  <Radio value="allowlist">allowlist</Radio>
                  <Radio value="private">private</Radio>
                </Radio.Group>
                <Select
                  mode="tags"
                  open={false}
                  placeholder="허용할 사번 입력 후 Enter"
                  disabled={visibility.code_visibility !== 'allowlist'}
                  value={visibility.allowlist}
                  onChange={(v) => setVis({ ...visibility, allowlist: v })}
                />
                <Button
                  type="primary"
                  onClick={() =>
                    action(
                      () => setVisibility(record.key, visibility.code_visibility, visibility.allowlist),
                      '공개범위를 저장했습니다',
                    )
                  }
                >
                  공개범위 저장
                </Button>
              </Space>
            </Card>
          )}

          <Modal
            title={`${record.key} 폐기`}
            open={deprecateOpen}
            okText="폐기"
            okButtonProps={{ danger: true }}
            cancelText="취소"
            onCancel={() => setDeprecateOpen(false)}
            onOk={() => {
              setDeprecateOpen(false)
              action(() => deprecate(target, record.key, replacedBy), '폐기했습니다')
            }}
          >
            <Input
              placeholder="대체 key (선택)"
              value={replacedBy}
              onChange={(e) => setReplacedBy(e.target.value)}
            />
          </Modal>
        </>
      )}
    </Space>
  )
}

export default function Admin() {
  return (
    <Card>
      <Tabs
        items={[
          { key: 'upload', label: '업로드', children: <UploadTab /> },
          { key: 'edit', label: '수정', children: <EditTab /> },
        ]}
      />
    </Card>
  )
}
