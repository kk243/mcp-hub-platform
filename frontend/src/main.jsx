import React from 'react'
import ReactDOM from 'react-dom/client'
import { RouterProvider } from 'react-router-dom'
import { ConfigProvider } from 'antd'
import koKR from 'antd/es/locale/ko_KR'
import { AllCommunityModule, ModuleRegistry } from 'ag-grid-community'
import 'antd/dist/antd.css'
import router from './routes'

ModuleRegistry.registerModules([AllCommunityModule])

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ConfigProvider locale={koKR}>
      <RouterProvider router={router} />
    </ConfigProvider>
  </React.StrictMode>,
)
