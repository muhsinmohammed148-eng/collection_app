import React, { useState, useMemo } from 'react';
import { 
  Users, 
  CreditCard, 
  BarChart3, 
  Grid, 
  Plus, 
  Search, 
  Filter, 
  Download, 
  CheckCircle2, 
  Clock, 
  AlertCircle, 
  TrendingUp, 
  DollarSign, 
  Calendar,
  ChevronRight,
  Menu,
  X,
  UserPlus,
  RefreshCw,
  Edit2,
  Trash2
} from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

// Initial Mock Data
const INITIAL_MEMBERS = [
  {
    id: 'm1',
    name: 'Sarah Jenkins',
    email: 'sarah.j@example.com',
    phone: '+1 (555) 234-5678',
    monthlyDue: 100,
    startDate: '2026-01-01',
    payments: [
      { id: 'p1', date: '2026-01-05', amount: 100, method: 'Bank Transfer', note: 'Jan Payment' },
      { id: 'p2', date: '2026-02-02', amount: 200, method: 'Credit Card', note: 'Feb & Mar Advance' },
    ]
  },
  {
    id: 'm2',
    name: 'Michael Chen',
    email: 'm.chen@techcorp.io',
    phone: '+1 (555) 876-5432',
    monthlyDue: 150,
    startDate: '2026-01-01',
    payments: [
      { id: 'p3', date: '2026-01-10', amount: 150, method: 'Cash', note: 'Jan Due' },
      { id: 'p4', date: '2026-02-15', amount: 75, method: 'Bank Transfer', note: 'Partial Feb' }
    ]
  },
  {
    id: 'm3',
    name: 'Elena Rostova',
    email: 'elena.rostova@design.co',
    phone: '+1 (555) 432-1098',
    monthlyDue: 80,
    startDate: '2026-01-01',
    payments: [
      { id: 'p5', date: '2026-01-02', amount: 480, method: 'Bank Transfer', note: '6 Months Advance' }
    ]
  },
  {
    id: 'm4',
    name: 'David Kalu',
    email: 'david.kalu@global.org',
    phone: '+1 (555) 901-2345',
    monthlyDue: 120,
    startDate: '2026-01-01',
    payments: []
  },
  {
    id: 'm5',
    name: 'Amara Okafor',
    email: 'amara.o@ventures.com',
    phone: '+1 (555) 654-9870',
    monthlyDue: 200,
    startDate: '2026-01-01',
    payments: [
      { id: 'p6', date: '2026-01-12', amount: 200, method: 'Credit Card', note: 'Jan Payment' },
      { id: 'p7', date: '2026-02-10', amount: 200, method: 'Credit Card', note: 'Feb Payment' },
      { id: 'p8', date: '2026-03-01', amount: 200, method: 'Credit Card', note: 'Mar Payment' }
    ]
  }
];

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const CURRENT_MONTH_INDEX = 2; // March (0-indexed for 2026 testing context)

export default function App() {
  const [members, setMembers] = useState(INITIAL_MEMBERS);
  const [activeTab, setActiveTab] = useState('dashboard'); // dashboard, members, matrix, payments
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Modal States
  const [isAddMemberOpen, setIsAddMemberOpen] = useState(false);
  const [isRecordPaymentOpen, setIsRecordPaymentOpen] = useState(false);
  const [selectedMemberId, setSelectedMemberId] = useState('');
  
  // New Member Form State
  const [newMember, setNewMember] = useState({
    name: '',
    email: '',
    phone: '',
    monthlyDue: 100,
    startDate: '2026-01-01'
  });

  // Payment Form State
  const [paymentForm, setPaymentForm] = useState({
    memberId: '',
    amount: '',
    date: new Date().toISOString().split('T')[0],
    method: 'Bank Transfer',
    note: ''
  });

  // Helper: Calculate member's monthly status mapping engine
  const calculateMemberLedger = (member) => {
    const totalPaid = member.payments.reduce((sum, p) => sum + Number(p.amount), 0);
    let remainingPool = totalPaid;

    const monthlyBreakdown = MONTHS.map((monthName, index) => {
      const due = member.monthlyDue;
      let allocated = 0;
      let status = 'unpaid';

      if (remainingPool >= due) {
        allocated = due;
        remainingPool -= due;
        status = 'paid';
      } else if (remainingPool > 0) {
        allocated = remainingPool;
        remainingPool = 0;
        status = 'partial';
      } else {
        allocated = 0;
        status = index <= CURRENT_MONTH_INDEX ? 'overdue' : 'unpaid';
      }

      return {
        month: monthName,
        monthIndex: index,
        due,
        allocated,
        balance: due - allocated,
        status
      };
    });

    const totalExpectedYTD = (CURRENT_MONTH_INDEX + 1) * member.monthlyDue;
    const currentBalanceOwed = Math.max(0, totalExpectedYTD - totalPaid);
    const advanceBalance = Math.max(0, totalPaid - totalExpectedYTD);

    let overallStatus = 'up-to-date';
    if (currentBalanceOwed > 0) {
      overallStatus = totalPaid > 0 ? 'behind' : 'unpaid';
    } else if (advanceBalance > 0) {
      overallStatus = 'advance';
    }

    return {
      totalPaid,
      monthlyBreakdown,
      currentBalanceOwed,
      advanceBalance,
      overallStatus
    };
  };

  // Memoized Calculated Data for all members
  const processedMembers = useMemo(() => {
    return members.map(m => ({
      ...m,
      ledger: calculateMemberLedger(m)
    }));
  }, [members]);

  // Dashboard Aggregated Analytics
  const metrics = useMemo(() => {
    let totalExpectedYTD = 0;
    let totalCollected = 0;
    let pendingDues = 0;
    let overdueCount = 0;

    processedMembers.forEach(m => {
      const expected = (CURRENT_MONTH_INDEX + 1) * m.monthlyDue;
      totalExpectedYTD += expected;
      totalCollected += m.ledger.totalPaid;
      pendingDues += m.ledger.currentBalanceOwed;
      if (m.ledger.overallStatus === 'unpaid' || m.ledger.overallStatus === 'behind') {
        overdueCount++;
      }
    });

    const collectionRate = totalExpectedYTD > 0 
      ? Math.min(100, Math.round((totalCollected / totalExpectedYTD) * 100)) 
      : 0;

    // Monthly Chart Data
    const monthlyChartData = MONTHS.map((month, idx) => {
      let expected = 0;
      let collected = 0;

      processedMembers.forEach(m => {
        expected += m.monthlyDue;
        collected += m.ledger.monthlyBreakdown[idx].allocated;
      });

      return { month, Expected: expected, Collected: collected };
    });

    // Pie chart distribution
    const statusCounts = {
      'Up to Date': processedMembers.filter(m => m.ledger.overallStatus === 'up-to-date').length,
      'In Advance': processedMembers.filter(m => m.ledger.overallStatus === 'advance').length,
      'Behind Dues': processedMembers.filter(m => m.ledger.overallStatus === 'behind').length,
      'Unpaid': processedMembers.filter(m => m.ledger.overallStatus === 'unpaid').length,
    };

    const statusPieData = Object.keys(statusCounts).map(key => ({
      name: key,
      value: statusCounts[key]
    }));

    return {
      totalExpectedYTD,
      totalCollected,
      pendingDues,
      collectionRate,
      overdueCount,
      monthlyChartData,
      statusPieData
    };
  }, [processedMembers]);

  // Filtered Members List for Search/Filter
  const filteredMembers = useMemo(() => {
    return processedMembers.filter(m => {
      const matchesSearch = m.name.toLowerCase().includes(searchQuery.toLowerCase()) || 
                            m.email.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesFilter = statusFilter === 'all' || m.ledger.overallStatus === statusFilter;
      return matchesSearch && matchesFilter;
    });
  }, [processedMembers, searchQuery, statusFilter]);

  // Handlers
  const handleAddMember = (e) => {
    e.preventDefault();
    if (!newMember.name || !newMember.monthlyDue) return;

    const created = {
      ...newMember,
      id: 'm_' + Date.now(),
      monthlyDue: Number(newMember.monthlyDue),
      payments: []
    };

    setMembers([...members, created]);
    setNewMember({ name: '', email: '', phone: '', monthlyDue: 100, startDate: '2026-01-01' });
    setIsAddMemberOpen(false);
  };

  const handleRecordPayment = (e) => {
    e.preventDefault();
    const targetId = paymentForm.memberId || selectedMemberId;
    if (!targetId || !paymentForm.amount) return;

    const paymentRecord = {
      id: 'p_' + Date.now(),
      date: paymentForm.date,
      amount: Number(paymentForm.amount),
      method: paymentForm.method,
      note: paymentForm.note
    };

    setMembers(members.map(m => {
      if (m.id === targetId) {
        return {
          ...m,
          payments: [paymentRecord, ...m.payments]
        };
      }
      return m;
    }));

    setPaymentForm({
      memberId: '',
      amount: '',
      date: new Date().toISOString().split('T')[0],
      method: 'Bank Transfer',
      note: ''
    });
    setIsRecordPaymentOpen(false);
    setSelectedMemberId('');
  };

  const handleDeleteMember = (id) => {
    if (window.confirm && window.confirm('Are you sure you want to delete this member?')) {
      setMembers(members.filter(m => m.id !== id));
    } else {
      setMembers(members.filter(m => m.id !== id));
    }
  };

  const exportCSV = () => {
    const headers = ['Member Name,Email,Monthly Due,Total Paid,Current Balance Owed,Status\n'];
    const rows = processedMembers.map(m => 
      `"${m.name}","${m.email}",${m.monthlyDue},${m.ledger.totalPaid},${m.ledger.currentBalanceOwed},"${m.ledger.overallStatus}"`
    );
    const blob = new Blob([headers.concat(rows.join('\n'))], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Collections_Report_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
  };

  const PIE_COLORS = ['#10B981', '#3B82F6', '#F59E0B', '#EF4444'];

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 flex flex-col font-sans">
      
      {/* HEADER / NAVIGATION */}
      <header className="bg-slate-900 text-white sticky top-0 z-30 shadow-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            
            {/* Logo & Title */}
            <div className="flex items-center space-x-3">
              <div className="bg-indigo-600 p-2 rounded-xl text-white shadow-lg">
                <CreditCard className="w-6 h-6" />
              </div>
              <div>
                <span className="font-bold text-lg tracking-tight text-white block leading-tight">PayFlow</span>
                <span className="text-xs text-slate-400 block hidden sm:block">Recurring Dues Manager</span>
              </div>
            </div>

            {/* Desktop Navigation */}
            <nav className="hidden md:flex space-x-1">
              <button 
                onClick={() => setActiveTab('dashboard')} 
                className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-medium transition ${activeTab === 'dashboard' ? 'bg-indigo-600 text-white' : 'text-slate-300 hover:bg-slate-800'}`}>
                <BarChart3 className="w-4 h-4" />
                <span>Dashboard</span>
              </button>
              <button 
                onClick={() => setActiveTab('members')} 
                className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-medium transition ${activeTab === 'members' ? 'bg-indigo-600 text-white' : 'text-slate-300 hover:bg-slate-800'}`}>
                <Users className="w-4 h-4" />
                <span>Members</span>
              </button>
              <button 
                onClick={() => setActiveTab('matrix')} 
                className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-medium transition ${activeTab === 'matrix' ? 'bg-indigo-600 text-white' : 'text-slate-300 hover:bg-slate-800'}`}>
                <Grid className="w-4 h-4" />
                <span>Monthly Matrix</span>
              </button>
            </nav>

            {/* Action Buttons */}
            <div className="hidden md:flex items-center space-x-3">
              <button
                onClick={() => setIsRecordPaymentOpen(true)}
                className="flex items-center space-x-2 bg-emerald-600 hover:bg-emerald-500 text-white px-3.5 py-2 rounded-lg text-sm font-medium shadow-sm transition">
                <Plus className="w-4 h-4" />
                <span>Record Payment</span>
              </button>
            </div>

            {/* Mobile Hamburger Menu Toggle */}
            <div className="md:hidden flex items-center space-x-2">
              <button
                onClick={() => setIsRecordPaymentOpen(true)}
                className="bg-emerald-600 text-white p-2 rounded-lg text-sm font-medium">
                <Plus className="w-5 h-5" />
              </button>
              <button
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                className="p-2 rounded-lg text-slate-300 hover:bg-slate-800 focus:outline-none">
                {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
              </button>
            </div>

          </div>
        </div>

        {/* Mobile Dropdown Nav */}
        {mobileMenuOpen && (
          <div className="md:hidden bg-slate-800 border-t border-slate-700 px-4 pt-2 pb-4 space-y-1">
            <button 
              onClick={() => { setActiveTab('dashboard'); setMobileMenuOpen(false); }} 
              className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-base font-medium ${activeTab === 'dashboard' ? 'bg-indigo-600 text-white' : 'text-slate-300 hover:bg-slate-700'}`}>
              <BarChart3 className="w-5 h-5" />
              <span>Dashboard Analytics</span>
            </button>
            <button 
              onClick={() => { setActiveTab('members'); setMobileMenuOpen(false); }} 
              className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-base font-medium ${activeTab === 'members' ? 'bg-indigo-600 text-white' : 'text-slate-300 hover:bg-slate-700'}`}>
              <Users className="w-5 h-5" />
              <span>Member Roster</span>
            </button>
            <button 
              onClick={() => { setActiveTab('matrix'); setMobileMenuOpen(false); }} 
              className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-base font-medium ${activeTab === 'matrix' ? 'bg-indigo-600 text-white' : 'text-slate-300 hover:bg-slate-700'}`}>
              <Grid className="w-5 h-5" />
              <span>Monthly Breakdown Grid</span>
            </button>
          </div>
        )}
      </header>

      {/* MAIN CONTAINER */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">

        {/* ========================================================
            TAB 1: DASHBOARD ANALYTICS
           ======================================================== */}
        {activeTab === 'dashboard' && (
          <div className="space-y-6 animate-fadeIn">
            
            {/* Top Stat Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Total Collected</p>
                  <h3 className="text-2xl font-extrabold text-slate-900 mt-1">${metrics.totalCollected.toLocaleString()}</h3>
                  <span className="text-xs text-emerald-600 font-medium inline-flex items-center mt-1">
                    <TrendingUp className="w-3 h-3 mr-1" /> Lifetime YTD
                  </span>
                </div>
                <div className="bg-emerald-50 p-3 rounded-xl text-emerald-600">
                  <DollarSign className="w-6 h-6" />
                </div>
              </div>

              <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Collection Rate</p>
                  <h3 className="text-2xl font-extrabold text-slate-900 mt-1">{metrics.collectionRate}%</h3>
                  <div className="w-24 bg-slate-100 rounded-full h-1.5 mt-2">
                    <div className="bg-indigo-600 h-1.5 rounded-full" style={{ width: `${Math.min(100, metrics.collectionRate)}%` }}></div>
                  </div>
                </div>
                <div className="bg-indigo-50 p-3 rounded-xl text-indigo-600">
                  <TrendingUp className="w-6 h-6" />
                </div>
              </div>

              <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Pending Dues</p>
                  <h3 className="text-2xl font-extrabold text-rose-600 mt-1">${metrics.pendingDues.toLocaleString()}</h3>
                  <span className="text-xs text-slate-400 block mt-1">Expected: ${metrics.totalExpectedYTD.toLocaleString()}</span>
                </div>
                <div className="bg-rose-50 p-3 rounded-xl text-rose-600">
                  <AlertCircle className="w-6 h-6" />
                </div>
              </div>

              <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Total Members</p>
                  <h3 className="text-2xl font-extrabold text-slate-900 mt-1">{members.length}</h3>
                  <span className="text-xs text-amber-600 font-medium inline-flex items-center mt-1">
                    {metrics.overdueCount} require attention
                  </span>
                </div>
                <div className="bg-amber-50 p-3 rounded-xl text-amber-600">
                  <Users className="w-6 h-6" />
                </div>
              </div>
            </div>

            {/* Charts Section */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              
              {/* Collection Trend */}
              <div className="lg:col-span-2 bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-base font-bold text-slate-900">Collection Trends (2026)</h3>
                    <p className="text-xs text-slate-500">Monthly expected versus actual collections</p>
                  </div>
                </div>
                <div className="h-64 sm:h-72 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={metrics.monthlyChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <defs>
                        <linearGradient id="colorCollected" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#10B981" stopOpacity={0.8}/>
                          <stop offset="95%" stopColor="#10B981" stopOpacity={0}/>
                        </linearGradient>
                        <linearGradient id="colorExpected" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#6366F1" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="#6366F1" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                      <XAxis dataKey="month" tick={{ fontSize: 12, fill: '#64748B' }} />
                      <YAxis tick={{ fontSize: 12, fill: '#64748B' }} />
                      <Tooltip 
                        contentStyle={{ backgroundColor: '#0F172A', borderRadius: '12px', color: '#fff', border: 'none' }} 
                        itemStyle={{ color: '#fff', fontSize: '12px' }}
                      />
                      <Area type="monotone" dataKey="Expected" stroke="#6366F1" fillOpacity={1} fill="url(#colorExpected)" strokeWidth={2} />
                      <Area type="monotone" dataKey="Collected" stroke="#10B981" fillOpacity={1} fill="url(#colorCollected)" strokeWidth={2} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Status Breakdown Pie */}
              <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm flex flex-col justify-between">
                <div>
                  <h3 className="text-base font-bold text-slate-900">Member Status Overview</h3>
                  <p className="text-xs text-slate-500 mb-4">Distribution by account standing</p>
                  
                  <div className="h-48 w-full flex items-center justify-center">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={metrics.statusPieData}
                          innerRadius={50}
                          outerRadius={75}
                          paddingAngle={4}
                          dataKey="value"
                        >
                          {metrics.statusPieData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-100">
                  {metrics.statusPieData.map((item, idx) => (
                    <div key={item.name} className="flex items-center space-x-2">
                      <span className="w-3 h-3 rounded-full inline-block" style={{ backgroundColor: PIE_COLORS[idx] }}></span>
                      <span className="text-xs font-medium text-slate-600">{item.name}: <strong className="text-slate-900">{item.value}</strong></span>
                    </div>
                  ))}
                </div>
              </div>

            </div>

            {/* Quick Actions & Recent Deficit Highlights */}
            <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden">
              <div className="p-5 border-b border-slate-100 flex items-center justify-between">
                <div>
                  <h3 className="text-base font-bold text-slate-900">Action Required: Overdue Accounts</h3>
                  <p className="text-xs text-slate-500">Members behind schedule for current billing period</p>
                </div>
                <button 
                  onClick={() => setActiveTab('members')}
                  className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 flex items-center">
                  View All <ChevronRight className="w-3 h-3 ml-1" />
                </button>
              </div>

              <div className="divide-y divide-slate-100">
                {processedMembers
                  .filter(m => m.ledger.overallStatus === 'behind' || m.ledger.overallStatus === 'unpaid')
                  .map(m => (
                    <div key={m.id} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-slate-50/50 transition">
                      <div className="flex items-center space-x-3">
                        <div className="w-10 h-10 rounded-full bg-rose-100 text-rose-700 font-bold flex items-center justify-center text-sm">
                          {m.name.charAt(0)}
                        </div>
                        <div>
                          <h4 className="text-sm font-semibold text-slate-900">{m.name}</h4>
                          <p className="text-xs text-slate-500">{m.email} • Due: ${m.monthlyDue}/mo</p>
                        </div>
                      </div>

                      <div className="flex items-center justify-between sm:justify-end space-x-4">
                        <div className="text-right">
                          <span className="text-xs text-slate-500 block">Balance Owed</span>
                          <span className="text-sm font-bold text-rose-600">${m.ledger.currentBalanceOwed}</span>
                        </div>
                        <button
                          onClick={() => {
                            setSelectedMemberId(m.id);
                            setPaymentForm(prev => ({ ...prev, memberId: m.id, amount: m.ledger.currentBalanceOwed }));
                            setIsRecordPaymentOpen(true);
                          }}
                          className="bg-slate-900 text-white text-xs px-3 py-1.5 rounded-lg hover:bg-slate-800 font-medium transition">
                          Collect
                        </button>
                      </div>
                    </div>
                  ))}
                {processedMembers.filter(m => m.ledger.overallStatus === 'behind' || m.ledger.overallStatus === 'unpaid').length === 0 && (
                  <div className="p-8 text-center text-slate-500 text-sm">
                    🎉 All members are currently up to date on their payments!
                  </div>
                )}
              </div>
            </div>

          </div>
        )}

        {/* ========================================================
            TAB 2: MEMBER MANAGEMENT
           ======================================================== */}
        {activeTab === 'members' && (
          <div className="space-y-4 animate-fadeIn">
            
            {/* Header / Filter Toolbar */}
            <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
              
              {/* Search Bar */}
              <div className="relative flex-1">
                <Search className="w-4 h-4 absolute left-3.5 top-3 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search members by name or email..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white"
                />
              </div>

              {/* Status Filter & Add Member */}
              <div className="flex flex-wrap items-center gap-3">
                <div className="flex items-center space-x-2">
                  <Filter className="w-4 h-4 text-slate-400" />
                  <select
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                    className="bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500">
                    <option value="all">All Statuses</option>
                    <option value="up-to-date">Up to Date</option>
                    <option value="advance">In Advance</option>
                    <option value="behind">Behind / Partial</option>
                    <option value="unpaid">Unpaid</option>
                  </select>
                </div>

                <button
                  onClick={exportCSV}
                  className="flex items-center space-x-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-2 rounded-xl text-sm font-medium transition">
                  <Download className="w-4 h-4" />
                  <span className="hidden sm:inline">Export</span>
                </button>

                <button
                  onClick={() => setIsAddMemberOpen(true)}
                  className="flex items-center space-x-2 bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-xl text-sm font-medium shadow-sm transition">
                  <UserPlus className="w-4 h-4" />
                  <span>Add Member</span>
                </button>
              </div>

            </div>

            {/* Member List Cards (Mobile & Responsive Grid) */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredMembers.map(m => {
                const { totalPaid, currentBalanceOwed, advanceBalance, overallStatus } = m.ledger;
                
                return (
                  <div key={m.id} className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-5 flex flex-col justify-between hover:shadow-md transition">
                    <div>
                      {/* Top Row: Avatar & Status Badge */}
                      <div className="flex items-start justify-between">
                        <div className="flex items-center space-x-3">
                          <div className="w-12 h-12 rounded-2xl bg-indigo-50 text-indigo-700 font-extrabold flex items-center justify-center text-lg border border-indigo-100">
                            {m.name.charAt(0)}
                          </div>
                          <div>
                            <h3 className="font-bold text-slate-900 text-base">{m.name}</h3>
                            <p className="text-xs text-slate-500 truncate max-w-[150px]">{m.email}</p>
                          </div>
                        </div>

                        {/* Status Badge */}
                        {overallStatus === 'up-to-date' && (
                          <span className="bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] uppercase tracking-wider font-semibold px-2 py-1 rounded-md inline-flex items-center">
                            <CheckCircle2 className="w-3 h-3 mr-1" /> Paid
                          </span>
                        )}
                        {overallStatus === 'advance' && (
                          <span className="bg-blue-50 text-blue-700 border border-blue-200 text-[10px] uppercase tracking-wider font-semibold px-2 py-1 rounded-md inline-flex items-center">
                            <Clock className="w-3 h-3 mr-1" /> Advance
                          </span>
                        )}
                        {(overallStatus === 'behind' || overallStatus === 'unpaid') && (
                          <span className="bg-rose-50 text-rose-700 border border-rose-200 text-[10px] uppercase tracking-wider font-semibold px-2 py-1 rounded-md inline-flex items-center">
                            <AlertCircle className="w-3 h-3 mr-1" /> Due
                          </span>
                        )}
                      </div>

                      {/* Details Box */}
                      <div className="mt-4 bg-slate-50 rounded-xl p-3 grid grid-cols-2 gap-2 text-xs">
                        <div>
                          <span className="text-slate-400 block">Monthly Rate</span>
                          <span className="font-bold text-slate-800">${m.monthlyDue}/mo</span>
                        </div>
                        <div>
                          <span className="text-slate-400 block">Total Paid YTD</span>
                          <span className="font-bold text-emerald-600">${totalPaid}</span>
                        </div>
                        <div>
                          <span className="text-slate-400 block">Balance Owed</span>
                          <span className={`font-bold ${currentBalanceOwed > 0 ? 'text-rose-600' : 'text-slate-700'}`}>
                            ${currentBalanceOwed}
                          </span>
                        </div>
                        <div>
                          <span className="text-slate-400 block">Credit Balance</span>
                          <span className="font-bold text-blue-600">${advanceBalance}</span>
                        </div>
                      </div>

                      {/* Payment History Log Summary */}
                      <div className="mt-4">
                        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-2">Recent Logs</span>
                        <div className="space-y-1.5">
                          {m.payments.slice(0, 2).map(p => (
                            <div key={p.id} className="flex justify-between text-xs text-slate-600 bg-white border border-slate-100 p-2 rounded-lg">
                              <span>{p.date} ({p.method})</span>
                              <span className="font-bold text-slate-900">+${p.amount}</span>
                            </div>
                          ))}
                          {m.payments.length === 0 && (
                            <p className="text-xs text-slate-400 italic">No payments logged yet.</p>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Bottom Actions */}
                    <div className="mt-5 pt-3 border-t border-slate-100 flex items-center justify-between">
                      <button
                        onClick={() => handleDeleteMember(m.id)}
                        className="text-slate-400 hover:text-rose-600 transition p-1">
                        <Trash2 className="w-4 h-4" />
                      </button>

                      <button
                        onClick={() => {
                          setSelectedMemberId(m.id);
                          setPaymentForm(prev => ({ 
                            ...prev, 
                            memberId: m.id, 
                            amount: currentBalanceOwed > 0 ? currentBalanceOwed : m.monthlyDue 
                          }));
                          setIsRecordPaymentOpen(true);
                        }}
                        className="flex items-center space-x-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs px-3.5 py-2 rounded-xl font-medium shadow-sm transition">
                        <Plus className="w-3.5 h-3.5" />
                        <span>Add Payment</span>
                      </button>
                    </div>

                  </div>
                );
              })}
            </div>

            {filteredMembers.length === 0 && (
              <div className="bg-white p-12 text-center rounded-2xl border border-slate-200/80">
                <Users className="w-12 h-12 text-slate-300 mx-auto mb-3" />
                <h3 className="text-base font-bold text-slate-700">No members found</h3>
                <p className="text-xs text-slate-400 mt-1">Try adjusting your search query or filters.</p>
              </div>
            )}

          </div>
        )}

        {/* ========================================================
            TAB 3: MONTHLY BREAKDOWN MATRIX GRID
           ======================================================== */}
        {activeTab === 'matrix' && (
          <div className="space-y-4 animate-fadeIn">
            <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-bold text-slate-900">2026 Monthly Breakdown Matrix</h2>
                <p className="text-xs text-slate-500">Auto-allocated payment mapping per billing period</p>
              </div>

              {/* Legend */}
              <div className="flex flex-wrap items-center gap-3 text-xs">
                <div className="flex items-center space-x-1">
                  <span className="w-3 h-3 rounded-md bg-emerald-500 block"></span>
                  <span className="text-slate-600">Paid</span>
                </div>
                <div className="flex items-center space-x-1">
                  <span className="w-3 h-3 rounded-md bg-amber-400 block"></span>
                  <span className="text-slate-600">Partial</span>
                </div>
                <div className="flex items-center space-x-1">
                  <span className="w-3 h-3 rounded-md bg-rose-500 block"></span>
                  <span className="text-slate-600">Overdue</span>
                </div>
                <div className="flex items-center space-x-1">
                  <span className="w-3 h-3 rounded-md bg-slate-200 block"></span>
                  <span className="text-slate-600">Upcoming</span>
                </div>
              </div>
            </div>

            {/* Matrix Table */}
            <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-x-auto">
              <table className="w-full text-left border-collapse min-w-[800px]">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                    <th className="py-3 px-4 sticky left-0 bg-slate-50 z-10">Member Name</th>
                    <th className="py-3 px-3 text-center">Due / Mo</th>
                    {MONTHS.map((m, idx) => (
                      <th key={m} className={`py-3 px-2 text-center ${idx === CURRENT_MONTH_INDEX ? 'bg-indigo-50 text-indigo-700 font-extrabold' : ''}`}>
                        {m}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-xs">
                  {processedMembers.map(m => (
                    <tr key={m.id} className="hover:bg-slate-50/60 transition">
                      
                      {/* Fixed Member Name Column */}
                      <td className="py-3 px-4 font-semibold text-slate-900 sticky left-0 bg-white shadow-sm z-10 flex items-center space-x-2">
                        <span className="w-7 h-7 rounded-full bg-slate-100 font-bold text-slate-700 flex items-center justify-center text-xs">
                          {m.name.charAt(0)}
                        </span>
                        <span className="truncate max-w-[120px]">{m.name}</span>
                      </td>

                      <td className="py-3 px-3 text-center font-medium text-slate-600">${m.monthlyDue}</td>

                      {/* Month Status Cells */}
                      {m.ledger.monthlyBreakdown.map((mb, idx) => {
                        let bgClass = 'bg-slate-100 text-slate-400';
                        let label = '$0';

                        if (mb.status === 'paid') {
                          bgClass = 'bg-emerald-500 text-white font-semibold';
                          label = `$${mb.allocated}`;
                        } else if (mb.status === 'partial') {
                          bgClass = 'bg-amber-400 text-slate-900 font-semibold';
                          label = `$${mb.allocated}`;
                        } else if (mb.status === 'overdue') {
                          bgClass = 'bg-rose-500 text-white font-semibold';
                          label = 'Unpaid';
                        }

                        return (
                          <td key={idx} className="py-2 px-1.5 text-center">
                            <div className={`py-1.5 px-1 rounded-lg text-[10px] shadow-2xs ${bgClass}`}>
                              {label}
                            </div>
                          </td>
                        );
                      })}

                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

      </main>

      {/* ========================================================
          MODAL 1: ADD MEMBER
         ======================================================== */}
      {isAddMemberOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs animate-fadeIn">
          <div className="bg-white w-full max-w-md rounded-2xl shadow-xl overflow-hidden border border-slate-100">
            <div className="px-6 py-4 bg-slate-900 text-white flex items-center justify-between">
              <h3 className="font-bold text-base flex items-center space-x-2">
                <UserPlus className="w-5 h-5 text-indigo-400" />
                <span>Add New Member</span>
              </h3>
              <button onClick={() => setIsAddMemberOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleAddMember} className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-600 uppercase mb-1">Full Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Jane Doe"
                  value={newMember.name}
                  onChange={(e) => setNewMember({ ...newMember, name: e.target.value })}
                  className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 uppercase mb-1">Email Address</label>
                <input
                  type="email"
                  placeholder="jane@example.com"
                  value={newMember.email}
                  onChange={(e) => setNewMember({ ...newMember, email: e.target.value })}
                  className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 uppercase mb-1">Monthly Due ($) *</label>
                  <input
                    type="number"
                    required
                    min="1"
                    value={newMember.monthlyDue}
                    onChange={(e) => setNewMember({ ...newMember, monthlyDue: e.target.value })}
                    className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 uppercase mb-1">Start Date</label>
                  <input
                    type="date"
                    value={newMember.startDate}
                    onChange={(e) => setNewMember({ ...newMember, startDate: e.target.value })}
                    className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              </div>

              <div className="pt-3 flex justify-end space-x-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsAddMemberOpen(false)}
                  className="px-4 py-2 bg-slate-100 text-slate-700 text-sm font-medium rounded-xl hover:bg-slate-200">
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-xl hover:bg-indigo-500 shadow-sm">
                  Save Member
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================
          MODAL 2: RECORD PAYMENT
         ======================================================== */}
      {isRecordPaymentOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs animate-fadeIn">
          <div className="bg-white w-full max-w-md rounded-2xl shadow-xl overflow-hidden border border-slate-100">
            <div className="px-6 py-4 bg-emerald-700 text-white flex items-center justify-between">
              <h3 className="font-bold text-base flex items-center space-x-2">
                <DollarSign className="w-5 h-5 text-emerald-300" />
                <span>Record Payment Entry</span>
              </h3>
              <button onClick={() => setIsRecordPaymentOpen(false)} className="text-emerald-200 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleRecordPayment} className="p-6 space-y-4">
              
              <div>
                <label className="block text-xs font-semibold text-slate-600 uppercase mb-1">Select Member *</label>
                <select
                  required
                  value={paymentForm.memberId || selectedMemberId}
                  onChange={(e) => setPaymentForm({ ...paymentForm, memberId: e.target.value })}
                  className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500">
                  <option value="">-- Choose Member --</option>
                  {processedMembers.map(m => (
                    <option key={m.id} value={m.id}>
                      {m.name} (${m.monthlyDue}/mo) - Owed: ${m.ledger.currentBalanceOwed}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 uppercase mb-1">Amount ($) *</label>
                  <input
                    type="number"
                    required
                    min="1"
                    placeholder="e.g. 200"
                    value={paymentForm.amount}
                    onChange={(e) => setPaymentForm({ ...paymentForm, amount: e.target.value })}
                    className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-600 uppercase mb-1">Payment Date</label>
                  <input
                    type="date"
                    required
                    value={paymentForm.date}
                    onChange={(e) => setPaymentForm({ ...paymentForm, date: e.target.value })}
                    className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 uppercase mb-1">Payment Method</label>
                <select
                  value={paymentForm.method}
                  onChange={(e) => setPaymentForm({ ...paymentForm, method: e.target.value })}
                  className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500">
                  <option value="Bank Transfer">Bank Transfer</option>
                  <option value="Cash">Cash</option>
                  <option value="Credit Card">Credit Card</option>
                  <option value="Check">Check</option>
                  <option value="Other">Other</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 uppercase mb-1">Notes / Description</label>
                <input
                  type="text"
                  placeholder="e.g. Paid 2 months in advance"
                  value={paymentForm.note}
                  onChange={(e) => setPaymentForm({ ...paymentForm, note: e.target.value })}
                  className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div className="bg-emerald-50 p-3 rounded-xl text-xs text-emerald-800 border border-emerald-100 flex items-start space-x-2">
                <RefreshCw className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                <span>
                  <strong>Auto-Allocation Engine:</strong> Entered payment will automatically cover past overdue months first, then current, and spill over into advance months.
                </span>
              </div>

              <div className="pt-3 flex justify-end space-x-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsRecordPaymentOpen(false)}
                  className="px-4 py-2 bg-slate-100 text-slate-700 text-sm font-medium rounded-xl hover:bg-slate-200">
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-emerald-600 text-white text-sm font-medium rounded-xl hover:bg-emerald-500 shadow-sm">
                  Register Payment
                </button>
              </div>

            </form>
          </div>
        </div>
      )}

    </div>
  );
}