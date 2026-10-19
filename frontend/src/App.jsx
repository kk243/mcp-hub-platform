import { useEffect, useState } from 'react'
import { Link, Outlet, useLocation } from 'react-router-dom'
import { Layout, Menu, message } from 'antd'
import { getMe } from './pages/hub/api'

export default function App() {
  const [me, setMe] = useState(null)
  const { pathname } = useLocation()

  useEffect(() => {
    getMe()
      .then(setMe)
      .catch((e) => {
        message.error(e.message)
        setMe({})
      })
  }, [])

  const menuItems = [
    { key: 'workflows', label: <Link to="/hub/workflows">Workflows</Link> },
    { key: 'tools', label: <Link to="/hub/tools">Tools</Link> },
    { key: 'skills', label: <Link to="/hub/skills">Skills</Link> },
    { key: 'admin', label: <Link to="/hub/admin">관리</Link> },
  ].filter(Boolean)

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Layout.Header style={{ display: 'flex', alignItems: 'center' }}>
        <div style={{ color: '#fff', fontWeight: 600, fontSize: 16, marginRight: 32 }}>Diff AI Agent Hub</div>
        <Menu
          theme="dark"
          mode="horizontal"
          selectedKeys={[pathname.split('/')[2]]}
          items={menuItems}
          style={{ flex: 1 }}
        />
        <span style={{ color: 'rgba(255,255,255,0.65)' }}>{me?.user_id}</span>
      </Layout.Header>
      <Layout.Content style={{ padding: 24 }}>
        <Outlet context={me} />
      </Layout.Content>
    </Layout>
  )
}
