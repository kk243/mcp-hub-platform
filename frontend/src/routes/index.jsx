import { createBrowserRouter, Navigate } from 'react-router-dom'
import App from '../App'
import HubList from '../pages/hub/HubList'
import WorkflowDetail from '../pages/hub/WorkflowDetail'
import ItemPage from '../pages/hub/ItemPage'
import Admin from '../pages/hub/Admin'

export const routes = [
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <Navigate to="/hub/workflows" replace /> },
      { path: 'hub', element: <Navigate to="/hub/workflows" replace /> },
      { path: 'hub/workflows', element: <HubList key="workflows" kind="workflows" /> },
      { path: 'hub/tools', element: <HubList key="tools" kind="tools" /> },
      { path: 'hub/skills', element: <HubList key="skills" kind="skills" /> },
      { path: 'hub/workflows/:key', element: <WorkflowDetail /> },
      { path: 'hub/tools/:key', element: <ItemPage /> },
      { path: 'hub/skills/:key', element: <ItemPage /> },
      { path: 'hub/admin', element: <Admin /> },
    ],
  },
]

export default createBrowserRouter(routes)
