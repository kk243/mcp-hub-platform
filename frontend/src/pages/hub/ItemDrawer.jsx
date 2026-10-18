import { Link } from 'react-router-dom'
import { Drawer } from 'antd'
import ItemDetail from './ItemDetail'

export default function ItemDrawer({ itemKey, type, title, onClose }) {
  return (
    <Drawer
      width={520}
      open={!!itemKey}
      title={title}
      onClose={onClose}
      extra={itemKey && <Link to={`/hub/${type}s/${itemKey}`}>전체 페이지</Link>}
      destroyOnClose
    >
      {itemKey && <ItemDetail itemKey={itemKey} />}
    </Drawer>
  )
}
