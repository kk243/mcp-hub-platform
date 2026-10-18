import { useParams } from 'react-router-dom'
import { Card } from 'antd'
import ItemDetail from './ItemDetail'
import './hub.css'

export default function ItemPage() {
  const { key } = useParams()
  return (
    <Card title="Tool / Skill 상세" style={{ maxWidth: 960 }}>
      <ItemDetail itemKey={key} />
    </Card>
  )
}
