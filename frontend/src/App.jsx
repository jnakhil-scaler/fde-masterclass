import { useState } from 'react'
import Overview from './pages/Overview'
import Orders from './pages/Orders'
import Customers from './pages/Customers'
import Suppliers from './pages/Suppliers'

const TABS = {
  Overview: Overview,
  Orders: Orders,
  Customers: Customers,
  Suppliers: Suppliers,
}

export default function App() {
  const [activeTab, setActiveTab] = useState('Overview')
  const ActiveComponent = TABS[activeTab]

  return (
    <div>
      <header className="app-header">
        <div className="brand">
          <span className="brand-mark">Gupta Building Materials</span>
          <span className="brand-tag">Indore, Madhya Pradesh</span>
        </div>
        <nav className="tabs" role="tablist">
          {Object.keys(TABS).map((tab) => (
            <button
              key={tab}
              className="tab"
              role="tab"
              aria-selected={activeTab === tab}
              onClick={() => setActiveTab(tab)}
            >
              {tab}
            </button>
          ))}
        </nav>
      </header>
      <main className="page">
        <ActiveComponent />
      </main>
    </div>
  )
}
