
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

const compactMoney = value =>
  new Intl.NumberFormat('en-AU', {
    style: 'currency',
    currency: 'AUD',
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(value)

const roundedAxisMoney = value => {
  const roundedValue = Math.round(value / 500) * 500
  return compactMoney(Object.is(roundedValue, -0) ? 0 : roundedValue)
}

function SpendingDonut({ spending, totalSpending }) {
  if (spending.length === 0) {
    return <p className="empty-state">No expenses for this period.</p>
  }

  return (
    <div className="spending-layout">
      <div
        className="donut-chart"
        style={{
          background: `conic-gradient(${spending
            .map((item, index) => {
              const start = spending
                .slice(0, index)
                .reduce(
                  (sum, previous) => sum + previous.amount,
                  0
                ) / totalSpending * 100

              const end = start + item.amount / totalSpending * 100
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
          <div className="legend-row" key={item.name}>
            <span
              className="legend-dot"
              style={{ background: item.color }}
            />
            <span className="legend-name">{item.name}</span>
            <strong>{money(item.amount)}</strong>
          </div>
        ))}
      </div>
    </div>
  )
}

function CashFlowGraph({ data, interval, availableIntervals, onIntervalChange }) {
  const [chartMode, setChartMode] = useState('income-expenses')

  if (data.length === 0) {
    return <p className="empty-state">No cash flow data for this period.</p>
  }

  const showsNet = chartMode === 'net'
  const chartHeight = 250
  const chartWidth = Math.max(760, data.length * 68)
  const padding = { top: 18, right: 22, bottom: 34, left: 54 }
  const plotWidth = chartWidth - padding.left - padding.right
  const plotHeight = chartHeight - padding.top - padding.bottom
  const values = data.flatMap(item =>
    showsNet ? [item.net] : [item.income, item.expenses]
  )
  const maxValue = Math.max(0, ...values)
  const minValue = Math.min(0, ...values)
  const valueRange = maxValue - minValue || 1
  const xFor = index =>
    padding.left + (data.length === 1
      ? plotWidth / 2
      : index / (data.length - 1) * plotWidth)
  const yFor = value =>
    padding.top + (maxValue - value) / valueRange * plotHeight
  const pointsFor = key =>
    data.map((item, index) => `${xFor(index)},${yFor(item[key])}`).join(' ')
  const gridValues = [...new Set([
    ...Array.from({ length: 5 }, (_, index) =>
      maxValue - valueRange * index / 4
    ),
    0,
  ])].sort((a, b) => b - a)
  const zeroPercent = `${((yFor(0) - padding.top) / plotHeight) * 100}%`

  return (
    <>
      <div className="cash-flow-controls">
        <label className="chart-interval-control">
          <span>Group by</span>
          <select
            value={interval}
            onChange={event => onIntervalChange(event.target.value)}
            aria-label="Group chart data by"
          >
            {availableIntervals.map(option => (
              <option key={option} value={option}>
                {option.charAt(0).toUpperCase() + option.slice(1)}
              </option>
            ))}
          </select>
        </label>

        <div className="chart-mode-toggle" role="group" aria-label="Chart view">
          <button
            className={!showsNet ? 'active' : ''}
            type="button"
            aria-pressed={!showsNet}
            onClick={() => setChartMode('income-expenses')}
          >
            Income &amp; expenses
          </button>
          <button
            className={showsNet ? 'active' : ''}
            type="button"
            aria-pressed={showsNet}
            onClick={() => setChartMode('net')}
          >
            Net cash flow
          </button>
        </div>

        <div className="cash-flow-legend" aria-label={`${showsNet ? 'Net cash flow' : 'Income and expenses'} series`}>
          {showsNet ? (
            <span><i className="series-key net-key" />Net cash flow</span>
          ) : (
            <>
              <span><i className="series-key income-key" />Income</span>
              <span><i className="series-key expense-key" />Expenses</span>
            </>
          )}
        </div>
      </div>

      <div className="cash-flow-chart-scroll">
        <svg
          className="cash-flow-chart"
          style={{ width: `${chartWidth}px` }}
          viewBox={`0 0 ${chartWidth} ${chartHeight}`}
          role="img"
          aria-label={showsNet ? 'Monthly net cash flow' : 'Monthly income and expenses'}
        >
          <title>{showsNet ? 'Monthly net cash flow' : 'Monthly income and expenses'}</title>

          <defs>
            <linearGradient
              id="net-flow-gradient"
              x1="0"
              y1={padding.top}
              x2="0"
              y2={chartHeight - padding.bottom}
              gradientUnits="userSpaceOnUse"
            >
              <stop offset="0%" stopColor="#22745f" />
              <stop offset={zeroPercent} stopColor="#22745f" />
              <stop offset={zeroPercent} stopColor="#b45454" />
              <stop offset="100%" stopColor="#b45454" />
            </linearGradient>
          </defs>

          {gridValues.map(value => (
            <g key={value}>
              <line
                className={value === 0 ? 'chart-zero-line' : 'chart-grid-line'}
                x1={padding.left}
                x2={chartWidth - padding.right}
                y1={yFor(value)}
                y2={yFor(value)}
              />
              {value !== 0 && (
                <text
                  className="chart-axis-label"
                  x={padding.left - 10}
                  y={yFor(value) + 4}
                  textAnchor="end"
                >
                  {roundedAxisMoney(value)}
                </text>
              )}
            </g>
          ))}

          {!showsNet && (
            <>
              <polyline className="cash-flow-line income-line" points={pointsFor('income')} />
              <polyline className="cash-flow-line expense-line" points={pointsFor('expenses')} />
            </>
          )}
          {showsNet && (
            <polyline
              className="cash-flow-line net-line"
              style={{ stroke: 'url(#net-flow-gradient)' }}
              points={pointsFor('net')}
            />
          )}

          {data.map((item, index) => (
            <text
              className="chart-month-label"
              key={item.key}
              x={xFor(index)}
              y={chartHeight - 10}
              textAnchor="middle"
            >
              {item.label}
            </text>
          ))}
        </svg>
      </div>

      <details className="cash-flow-data">
        <summary>View monthly cash flow data</summary>
        <div className="cash-flow-table-scroll">
          <table>
            <thead>
              <tr>
                <th>Period</th>
                <th className="right-align">Income</th>
                <th className="right-align">Expenses</th>
                <th className="right-align">Investments</th>
                <th className="right-align">Net cash flow</th>
              </tr>
            </thead>
            <tbody>
              {data.map(item => (
                <tr key={item.key}>
                  <td>{item.label}</td>
                  <td className="right-align">{money(item.income)}</td>
                  <td className="right-align">{money(item.expenses)}</td>
                  <td className="right-align">{money(item.investments)}</td>
                  <td className={`right-align ${item.net >= 0 ? 'positive' : 'negative'}`}>
                    {money(item.net)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </>
  )
}

function App() {
  const [transactions, setTransactions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [activePage, setActivePage] = useState('Overview')
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('All categories')
  const [period, setPeriod] = useState('This month')
  const [cashFlowInterval, setCashFlowInterval] = useState('month')

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

  const transactionDates = periodTransactions
    .map(transaction => new Date(`${transaction.date}T00:00:00`).getTime())
    .filter(Number.isFinite)
  const selectedRangeDays = period === 'All time'
    ? transactionDates.length > 1
      ? (Math.max(...transactionDates) - Math.min(...transactionDates)) /
        (1000 * 60 * 60 * 24) + 1
      : 0
    : period === 'This month' || period === 'Last month'
      ? 31
      : period === 'Last 3 months'
        ? 92
        : 365
  const availableCashFlowIntervals = [
    ...(selectedRangeDays <= 365 ? ['day'] : []),
    'week',
    ...(selectedRangeDays >= 60 ? ['month'] : []),
  ]
  const selectedCashFlowInterval = availableCashFlowIntervals.includes(
    cashFlowInterval
  )
    ? cashFlowInterval
    : availableCashFlowIntervals[0]

  const isTransfer = transaction =>
    transaction.cash_flow_type === 'internal_transfer'

  // Transfers should remain in the database for lookups, but not count
  // towards income/expense totals or spending breakdowns.
  const summaryTransactions = periodTransactions.filter(
    transaction => !isTransfer(transaction)
  )

  const totalIncome = summaryTransactions
    .filter(transaction => transaction.cash_flow_type === 'income')
    .reduce((sum, transaction) => sum + transaction.amount, 0)

  const totalExpenses = summaryTransactions
    .filter(transaction => transaction.cash_flow_type === 'expense')
    .reduce(
      (sum, transaction) => sum + Math.abs(transaction.amount),
      0
    )

  const totalInvestments = summaryTransactions
    .filter(transaction => transaction.cash_flow_type === 'investment')
    .reduce(
      (sum, transaction) => sum + Math.abs(transaction.amount),
      0
    )

  const spending = Object.values(
    summaryTransactions.reduce((groups, transaction) => {
      if (transaction.cash_flow_type !== 'expense') return groups

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

  const cashFlowData = Object.values(
    summaryTransactions.reduce((groups, transaction) => {
      const transactionDate = new Date(`${transaction.date}T00:00:00`)
      const periodDate = new Date(transactionDate)

      if (selectedCashFlowInterval === 'week') {
        const dayOfWeek = periodDate.getDay()
        const daysSinceMonday = (dayOfWeek + 6) % 7
        periodDate.setDate(periodDate.getDate() - daysSinceMonday)
      } else if (selectedCashFlowInterval === 'month') {
        periodDate.setDate(1)
      }

      const key = `${periodDate.getFullYear()}-${String(
        periodDate.getMonth() + 1
      ).padStart(2, '0')}-${String(periodDate.getDate()).padStart(2, '0')}`

      if (!groups[key]) {
        groups[key] = {
          key,
          label:
            selectedCashFlowInterval === 'day'
              ? transactionDate.toLocaleDateString('en-AU', {
                day: 'numeric',
                month: 'short',
              })
              : selectedCashFlowInterval === 'week'
                ? periodDate.toLocaleDateString('en-AU', {
                  day: 'numeric',
                  month: 'short',
                })
                : periodDate.toLocaleDateString('en-AU', {
                  month: 'short',
                  year: '2-digit',
                }),
          income: 0,
          expenses: 0,
          investments: 0,
          net: 0,
        }
      }

      if (transaction.cash_flow_type === 'income') {
        groups[key].income += transaction.amount
      } else if (transaction.cash_flow_type === 'expense') {
        groups[key].expenses += Math.abs(transaction.amount)
      } else if (transaction.cash_flow_type === 'investment') {
        groups[key].investments += Math.abs(transaction.amount)
      }

      groups[key].net =
        groups[key].income -
        groups[key].expenses -
        groups[key].investments
      return groups
    }, {})
  ).sort((a, b) => a.key.localeCompare(b.key))

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
                  <p className="metric-note">Ordinary spending</p>
                </article>

                <article className="summary-card balance-card">
                  <div className="card-topline">
                    <span>Net cash flow</span>
                    <span className="metric-icon balance-icon">＝</span>
                  </div>
                  <h2
                    className={
                      totalIncome - totalExpenses - totalInvestments >= 0
                        ? 'positive'
                        : 'negative'
                    }
                  >
                    {money(
                      totalIncome - totalExpenses - totalInvestments
                    )}
                  </h2>
                  <p className="metric-note">
                    After expenses and investments
                  </p>
                </article>
              </section>

              <section className="content-grid">
                <article className="panel cash-flow-panel">
                  <div className="panel-heading">
                    <div>
                      <h3>
                        {selectedCashFlowInterval === 'day'
                          ? 'Daily cash flow'
                          : selectedCashFlowInterval === 'week'
                            ? 'Weekly cash flow'
                            : 'Monthly cash flow'}
                      </h3>
                      <p>Income, spending, investments and net movement</p>
                    </div>
                  </div>

                  <CashFlowGraph
                    data={cashFlowData}
                    interval={selectedCashFlowInterval}
                    availableIntervals={availableCashFlowIntervals}
                    onIntervalChange={setCashFlowInterval}
                  />
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
                          <span>{transaction.date} · {transaction.category}</span>
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

              <SpendingDonut
                spending={spending}
                totalSpending={totalSpending}
              />

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
          Review vendors currently classified as Other or Transfer.
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
