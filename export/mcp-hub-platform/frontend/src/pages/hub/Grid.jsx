import { AgGridReact } from 'ag-grid-react'
import { themeQuartz } from 'ag-grid-community'
import { Tag } from 'antd'

const theme = themeQuartz.withParams({
  fontFamily: 'inherit',
  fontSize: 14,
  accentColor: '#1890ff',
  headerFontWeight: 600,
})

const defaultColDef = { sortable: true, filter: true, resizable: true, flex: 1, minWidth: 90 }
const rowClassRules = { 'row-deprecated': (p) => !!p.data?.deprecated }
const localeText = { noRowsToShow: '데이터가 없습니다' }

export const VISIBILITY = { public: '공개', allowlist: '허용목록', private: '비공개' }

export function TagsCell({ value }) {
  return (value || []).map((t) => <Tag key={t}>{t}</Tag>)
}

// autoHeight: 스키마처럼 작은 표는 내용 높이에 맞춘다
export default function Grid({ height = 520, autoHeight = false, onRowClicked, ...props }) {
  return (
    <div style={autoHeight ? undefined : { height }}>
      <AgGridReact
        theme={theme}
        domLayout={autoHeight ? 'autoHeight' : 'normal'}
        defaultColDef={defaultColDef}
        rowClassRules={rowClassRules}
        localeText={localeText}
        onRowClicked={onRowClicked}
        rowStyle={onRowClicked ? { cursor: 'pointer' } : undefined}
        {...props}
      />
    </div>
  )
}
