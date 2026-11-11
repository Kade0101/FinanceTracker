
import { useEffect, useState } from 'react'
import './App.css'

const money = value =>
  new Intl.NumberFormat('en-AU', {
    style: 'currency',
    currency: 'AUD',
  }).format(value)

const categoryColors = [
  '#7c9cff',
  '#55c5a5',
  '#e8b86d',
  '#bd91f5',
  '#f08e9c',
  '#78b8e8',
  '#e89b55',
  '#8dcf80',
]

function App() {
  const [transactions, setTransactions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [activePage, setActivePage] = useState('Overview')
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('All categories')
  const [period, setPeriod] = useState('This month')

  const [processing, setProcessing] = useState(false)
  const [processResult, setProcessResult] = useState('')
  const [processError, setProcessError] = useState('')
  const [progress, setProgress] = useState(null)

  const [reviewVendors, setReviewVendors] = useState([])
  const [availableCategories, setAvailableCategories] = useState([])
  const [vendorSelections, setVendorSelections] = useState({})
  const [reviewLoading, setReviewLoading] = useState(false)
  const [reviewSaving, setReviewSaving] = useState(false)
  const [reviewError, setReviewError] = useState('')
  const [reviewMessage, setReviewMessage] = useState('')

  const loadTransactions = () =>
    fetch('http://127.0.0.1:8000/transactions')
      .then(response => {
        if (!response.ok) {
          throw new Error('Failed to load transactions')
        }
        return response.json()
      })
      .then(data => {
        const formattedTransactions = data.map(transaction => ({
          ...transaction,
          vendor:
            transaction.vendor ||
            transaction.description ||
            'Unknown',
          category: transaction.category || 'Uncategorised',
          amount:
            Number(transaction.credit || 0) +
            Number(transaction.debit || 0),
        }))

        setTransactions(formattedTransactions)
      })

  const loadVendorReview = () => {
    setReviewLoading(true)
    setReviewError('')

    fetch('http://127.0.0.1:8000/vendors/review')
      .then(response => {
        if (!response.ok) {
          throw new Error('Failed to load vendors for review')
        }
        return response.json()
      })
      .then(data => {
        setReviewVendors(data.vendors)
        setAvailableCategories(data.categories)
      })
      .catch(err => setReviewError(err.message))
      .finally(() => setReviewLoading(false))
  }

  const handleSaveVendorCategories = () => {
    const selections = reviewVendors
      .filter(vendor => vendorSelections[vendor.id])
      .map(vendor => ({
        vendor_id: vendor.id,
        category: vendorSelections[vendor.id],
      }))

    if (selections.length === 0) {
      setReviewError('Please select a category for at least one vendor.')
      return
    }

    setReviewSaving(true)
    setReviewError('')
    setReviewMessage('')

    fetch('http://127.0.0.1:8000/vendors/review', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ selections }),
    })
      .then(async response => {
        const data = await response.json()

        if (!response.ok) {
          throw new Error(data.detail || 'Failed to save categories')
        }

        return data
      })
      .then(data => {
        setReviewMessage(
          `Successfully updated ${data.updated_vendors} vendors.`
        )
        setVendorSelections({})
        loadTransactions()
        loadVendorReview()
      })
      .catch(err => setReviewError(err.message))
      .finally(() => setReviewSaving(false))
  }

  useEffect(() => {
    loadTransactions()
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
  if (activePage === 'Vendor Review') {
    loadVendorReview()
  }
}, [activePage])

  const finishProcessing = status => {
    setProgress(null)
    setProcessing(false)

    if (status.error) {
      setProcessError(status.error)
      return
    }

  

    const stats = status.result
    if (stats) {
      setProcessResult(
        `Imported ${stats.imported} new transactions ` +
          `(${stats.duplicates_skipped} duplicates skipped), ` +
          `categorised ${stats.categorised} ` +
          `in ${stats.elapsed_seconds}s.`
      )
      loadTransactions().catch(err => setProcessError(err.message))
    }
  }

  const pollProcessStatus = () => {
    fetch('http://127.0.0.1:8000/process-csv/status')
      .then(response => {
        if (!response.ok) {
          throw new Error('Failed to check processing status')
        }
        return response.json()
      })
      .then(status => {
        if (status.active) {
          setProgress({
            stage: status.stage,
            current: status.current,
            total: status.total,
          })
          setTimeout(pollProcessStatus, 400)
          return
        }

        finishProcessing(status)
      })
      .catch(err => {
        setProcessError(err.message)
        setProgress(null)
        setProcessing(false)
      })
  }

  const handleProcessCsv = () => {
    setProcessing(true)
    setProcessResult('')
    setProcessError('')
    setProgress({ stage: 'Starting', current: 0, total: 0 })

    fetch('http://127.0.0.1:8000/process-csv', { method: 'POST' })
      .then(async response => {
        if (!response.ok) {
          const body = await response.json().catch(() => null)
          throw new Error(
            body?.detail || 'Failed to start CSV processing'
          )
        }
        pollProcessStatus()
      })
      .catch(err => {
        setProcessError(err.message)
        setProgress(null)
        setProcessing(false)
      })
  }

  const getDateRange = () => {
    const now = new Date()
    const start = new Date(now.getFullYear(), now.getMonth(), 1)
    const end = new Date(now.getFullYear(), now.getMonth() + 1, 1)

    if (period === 'Last month') {
      start.setMonth(start.getMonth() - 1)
      end.setMonth(end.getMonth() - 1)
    } else if (period === 'Last 3 months') {
      start.setMonth(start.getMonth() - 2)
    } else if (period === 'This year') {
      start.setMonth(0)
      start.setDate(1)
    }

    return { start, end }
  }

  const { start: periodStart, end: periodEnd } = getDateRange()

const periodTransactions = transactions.filter(transaction => {
  if (period === 'All time') {
    return true
  }

  const transactionDate = new Date(`${transaction.date}T00:00:00`)

  if (period === 'Last 3 months') {
    return transactionDate >= periodStart &&
      transactionDate <= new Date()
  }

  if (period === 'This year') {
    return transactionDate >= periodStart &&
      transactionDate <= new Date()
  }

  return transactionDate >= periodStart &&
    transactionDate < periodEnd
})

  const isTransfer = transaction => {
    const categoryName = (transaction.category || '').toLowerCase()
    return categoryName === 'transfer' || categoryName === 'internal transfer'
  }

  // Transfers should remain in the database for lookups, but not count
  // towards income/expense totals or spending breakdowns.
  const summaryTransactions = periodTransactions.filter(
    transaction => !isTransfer(transaction)
  )

  const totalIncome = summaryTransactions
    .filter(transaction => transaction.amount > 0)
    .reduce((sum, transaction) => sum + transaction.amount, 0)

  const totalExpenses = summaryTransactions
    .filter(transaction => transaction.amount < 0)
    .reduce(
      (sum, transaction) => sum + Math.abs(transaction.amount),
      0
    )

  const spending = Object.values(
    summaryTransactions.reduce((groups, transaction) => {
      if (transaction.amount >= 0) return groups

      const name = transaction.category

      if (!groups[name]) {
        groups[name] = {
          name,
          amount: 0,
        }
      }

      groups[name].amount += Math.abs(transaction.amount)
      return groups
    }, {})
  )
    .map((item, index) => ({
      ...item,
      color: categoryColors[index % categoryColors.length],
    }))
    .sort((a, b) => b.amount - a.amount)

  const totalSpending = spending.reduce(
    (sum, item) => sum + item.amount,
    0
  )

  const filteredTransactions = periodTransactions.filter(transaction => {
    const matchesSearch =
      `${transaction.vendor} ${transaction.description} ${transaction.category}`
        .toLowerCase()
        .includes(search.toLowerCase())

    const matchesCategory =
      category === 'All categories' ||
      transaction.category === category

    return matchesSearch && matchesCategory
  })

const navItems = [
  { name: 'Overview', icon: '◫' },
  { name: 'Transactions', icon: '⇄' },
  { name: 'Categories', icon: '▦' },
  { name: 'Vendor Review', icon: '✓' },
]

  const recentTransactions = [...periodTransactions]
    .sort((a, b) => {
      if (a.date !== b.date) {
        return b.date.localeCompare(a.date)
      }
      return (b.id || 0) - (a.id || 0)
    })
    .slice(0, 5)

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">F</div>
          <span>
            Finance<span className="brand-light">Tracker</span>
          </span>
        </div>

        <div className="nav-label">WORKSPACE</div>

        <nav>
          {navItems.map(item => (
            <button
              key={item.name}
              className={`nav-item ${
                activePage === item.name ? 'active' : ''
              }`}
              onClick={() => setActivePage(item.name)}
            >
              <span className="nav-icon">{item.icon}</span>
              {item.name}
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="profile-avatar">KG</div>
          <div className="profile-info">
            <strong>My finances</strong>
            <span>Personal account</span>
          </div>
          <span className="profile-menu">···</span>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="breadcrumb">
            Workspace <span>/</span> {activePage}
          </div>

          <div className="topbar-right">
            <button
              className="process-button"
              onClick={handleProcessCsv}
              disabled={processing}
            >
              {processing ? 'Processing...' : 'Process CSV'}
            </button>
            <span className="demo-badge">LIVE DATA</span>
            <div className="topbar-avatar">KG</div>
          </div>
        </header>

        <div className="page-content">
          {loading && (
            <p className="metric-note">Loading your transactions...</p>
          )}

          {error && (
            <p className="error-message">
              Could not load transactions: {error}
            </p>
          )}

          {processing && progress && (
            <div className="process-progress">
              <div className="process-progress-top">
                <span>{progress.stage}</span>
                <span>
                  {progress.total > 0
                    ? `${Math.round(
                        (progress.current / progress.total) * 100
                      )}% (${progress.current}/${progress.total})`
                    : '0%'}
                </span>
              </div>
              <div className="progress-track">
                <div
                  className="progress-fill"
                  style={{
                    width: `${
                      progress.total > 0
                        ? (progress.current / progress.total) * 100
                        : 0
                    }%`,
                    background: '#7c9cff',
                  }}
                />
              </div>
            </div>
          )}

          {processResult && (
            <p className="process-result">{processResult}</p>
          )}

          {processError && (
            <p className="error-message">
              Could not process the CSV: {processError}
            </p>
          )}

          {!loading && !error && transactions.length === 0 && (
            <p className="metric-note">
              No transactions found in your database.
            </p>
          )}

          <section className="page-heading">
            <div>
              <p className="eyebrow">YOUR MONEY, AT A GLANCE</p>
              <h1>{activePage}</h1>
              <p className="subtitle">
                Here's what's happening with your finances.
              </p>
            </div>

            <select
              className="period-select"
              value={period}
              onChange={event => setPeriod(event.target.value)}
              aria-label="Select reporting period"
            >
              <option>All time</option>
              <option>This month</option>
              <option>Last month</option>
              <option>Last 3 months</option>
              <option>This year</option>
            </select>
          </section>

          {activePage === 'Overview' && (
            <>
              <section className="summary-grid">
                <article className="summary-card">
                  <div className="card-topline">
                    <span>Total income</span>
                    <span className="metric-icon income-icon">↙</span>
                  </div>
                  <h2>{money(totalIncome)}</h2>
                  <p className="metric-note">Money received</p>
                </article>

                <article className="summary-card">
                  <div className="card-topline">
                    <span>Total expenses</span>
                    <span className="metric-icon expense-icon">↗</span>
                  </div>
                  <h2>{money(totalExpenses)}</h2>
                  <p className="metric-note">Money spent</p>
                </article>

                <article className="summary-card balance-card">
                  <div className="card-topline">
                    <span>Net cash flow</span>
                    <span className="metric-icon balance-icon">＝</span>
                  </div>
                  <h2
                    className={
                      totalIncome - totalExpenses >= 0
                        ? 'positive'
                        : 'negative'
                    }
                  >
                    {money(totalIncome - totalExpenses)}
                  </h2>
                  <p className="metric-note">
                    Income minus expenses
                  </p>
                </article>
              </section>

              <section className="content-grid">
                <article className="panel spending-panel">
                  <div className="panel-heading">
                    <div>
                      <h3>Spending breakdown</h3>
                      <p>Where your money goes</p>
                    </div>
                    <span className="panel-menu">···</span>
                  </div>

                  {spending.length === 0 ? (
                    <p className="empty-state">
                      No expenses for this period.
                    </p>
                  ) : (
                    <div className="spending-layout">
                      <div
                        className="donut-chart"
                        style={{
                          background: `conic-gradient(${spending
                            .map((item, index) => {
                              const start = spending
                                .slice(0, index)
                                .reduce(
                                  (sum, previous) =>
                                    sum + previous.amount,
                                  0
                                ) / totalSpending * 100

                              const end =
                                start +
                                item.amount / totalSpending * 100

                              return `${item.color} ${start}% ${end}%`
                            })
                            .join(', ')})`,
                        }}
                      >
                        <div className="donut-hole">
                          <span>Total spent</span>
                          <strong>{money(totalSpending)}</strong>
                        </div>
                      </div>

                      <div className="legend">
                        {spending.map(item => (
                          <div
                            className="legend-row"
                            key={item.name}
                          >
                            <span
                              className="legend-dot"
                              style={{ background: item.color }}
                            />
                            <span className="legend-name">
                              {item.name}
                            </span>
                            <strong>{money(item.amount)}</strong>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </article>

                <article className="panel activity-panel">
                  <div className="panel-heading">
                    <div>
                      <h3>Recent activity</h3>
                      <p>Your latest transactions</p>
                    </div>
                    <button
                      className="text-button"
                      onClick={() => setActivePage('Transactions')}
                    >
                      View all →
                    </button>
                  </div>

                  <div className="recent-list">
                    {recentTransactions.map((transaction, index) => (
                      <div
                        className="recent-row"
                        key={transaction.id ?? `${transaction.date}-${index}`}
                      >
                        <div
                          className={`transaction-avatar avatar-${index % 5}`}
                        >
                          {transaction.vendor.charAt(0).toUpperCase()}
                        </div>

                        <div className="recent-details">
                          <strong>{transaction.vendor}</strong>
                          <span>{transaction.category}</span>
                        </div>

                        <strong
                          className={
                            transaction.amount > 0
                              ? 'positive'
                              : 'amount'
                          }
                        >
                          {transaction.amount > 0 ? '+' : '−'}
                          {money(Math.abs(transaction.amount))}
                        </strong>
                      </div>
                    ))}

                    {!loading && recentTransactions.length === 0 && (
                      <p className="empty-state">
                        No transactions for this period.
                      </p>
                    )}
                  </div>
                </article>
              </section>
            </>
          )}

          {activePage === 'Categories' && (
            <section className="panel category-page">
              <div className="panel-heading">
                <div>
                  <h3>Spending by category</h3>
                  <p>Your spending for the selected period</p>
                </div>
              </div>

              {spending.map(item => (
                <div className="category-item" key={item.name}>
                  <div className="category-item-top">
                    <span>{item.name}</span>
                    <strong>{money(item.amount)}</strong>
                  </div>

                  <div className="progress-track">
                    <div
                      className="progress-fill"
                      style={{
                        width: `${
                          totalSpending > 0
                            ? item.amount / totalSpending * 100
                            : 0
                        }%`,
                        background: item.color,
                      }}
                    />
                  </div>
                </div>
              ))}

              {spending.length === 0 && (
                <p className="empty-state">
                  No spending categories for this period.
                </p>
              )}
            </section>
          )}

          {activePage === 'Vendor Review' && (
  <section className="panel vendor-review-panel">
    <div className="panel-heading">
      <div>
        <h3>Vendors requiring review</h3>
        <p>
          Assign categories to vendors currently classified as Other.
        </p>
      </div>
      <span className="review-count">
        {reviewVendors.length} vendors
      </span>
    </div>

    {reviewLoading && (
      <p className="empty-state">Loading vendors...</p>
    )}

    {reviewError && (
      <p className="error-message">{reviewError}</p>
    )}

    {reviewMessage && (
      <p className="process-result">{reviewMessage}</p>
    )}

    {!reviewLoading && reviewVendors.length > 0 && (
      <>
        <div className="vendor-review-list">
          {reviewVendors.map(vendor => (
            <div className="vendor-review-row" key={vendor.id}>
              <div className="vendor-review-details">
                <strong>{vendor.vendor_name}</strong>
                <span>
                  {vendor.transaction_count} transactions
                </span>
              </div>

              <div className="vendor-review-spending">
                {money(vendor.total_spent)}
              </div>

              <select
                className="vendor-category-select"
                value={vendorSelections[vendor.id] || ''}
                onChange={event =>
                  setVendorSelections(previous => ({
                    ...previous,
                    [vendor.id]: event.target.value,
                  }))
                }
                aria-label={`Category for ${vendor.vendor_name}`}
              >
                <option value="">Select category</option>

                {availableCategories.map(item => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </div>
          ))}
        </div>

        <div className="vendor-review-footer">
          <span>
            {Object.keys(vendorSelections).length} categories selected
          </span>

          <button
            className="save-categories-button"
            onClick={handleSaveVendorCategories}
            disabled={
              reviewSaving ||
              Object.keys(vendorSelections).length === 0
            }
          >
            {reviewSaving ? 'Saving...' : 'Save Categories'}
          </button>
        </div>
      </>
    )}

    {!reviewLoading && reviewVendors.length === 0 && !reviewError && (
      <p className="empty-state">
        No vendors currently require review.
      </p>
    )}
  </section>
)}

          {activePage === 'Transactions' && (
            <section className="panel transactions-panel">
              <div className="panel-heading">
                <div>
                  <h3>All transactions</h3>
                  <p>
                    Search and filter your activity (
                    {filteredTransactions.length} shown)
                  </p>
                </div>
              </div>

              <div className="table-controls">
                <input
                  type="search"
                  placeholder="Search transactions..."
                  value={search}
                  onChange={event => setSearch(event.target.value)}
                />

                <select
                  value={category}
                  onChange={event => setCategory(event.target.value)}
                  aria-label="Filter by category"
                >
                  <option>All categories</option>
                  {[
                    ...new Set(
                      transactions
                        .map(transaction => transaction.category)
                        .filter(Boolean)
                    ),
                  ]
                    .sort()
                    .map(item => (
                      <option key={item} value={item}>
                        {item}
                      </option>
                    ))}
                </select>
              </div>

              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Transaction</th>
                      <th>Category</th>
                      <th className="right-align">Amount</th>
                    </tr>
                  </thead>

                  <tbody>
                    {filteredTransactions.map((transaction, index) => (
                      <tr
                        key={transaction.id ?? `${transaction.date}-${index}`}
                      >
                        <td>{transaction.date}</td>

                        <td>
                          <div className="table-vendor">
                            {transaction.vendor}
                          </div>
                          <div className="table-description">
                            {transaction.description}
                          </div>
                        </td>

                        <td>
                          <span className="category-tag">
                            {transaction.category}
                          </span>
                        </td>

                        <td
                          className={`right-align ${
                            transaction.amount > 0
                              ? 'positive'
                              : 'amount'
                          }`}
                        >
                          {transaction.amount > 0 ? '+' : '−'}
                          {money(Math.abs(transaction.amount))}
                        </td>
                      </tr>
                    ))}

                    {filteredTransactions.length === 0 && (
                      <tr>
                        <td colSpan="4" className="empty-state">
                          No matching transactions found.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          <footer className="page-footer">
            <span>FinanceTracker</span>
            <span>Personal finance, made clearer.</span>
          </footer>
        </div>
      </main>
    </div>
  )
}

export default App
