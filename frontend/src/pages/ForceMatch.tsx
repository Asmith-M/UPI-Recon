import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Input } from "../components/ui/input";
import { Button } from "../components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Badge } from "../components/ui/badge";
import { Loader2, CheckCircle2, AlertCircle, Search, RefreshCw, ArrowRight, ArrowLeft, ZoomIn, Calendar, Clock, FileText, Hash, TrendingUp, TrendingDown } from "lucide-react";
import { apiClient } from "../lib/api";
import { useToast } from "../hooks/use-toast";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Separator } from "../components/ui/separator";
import {
  Alert,
  AlertDescription,
  AlertTitle,
} from "../components/ui/alert";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "../components/ui/collapsible";
import { ChevronDown, ChevronUp } from "lucide-react";

interface TransactionDetail {
  rrn: string;
  amount: number;
  date: string;
  time?: string;
  description?: string;
  reference?: string;
  debit_credit?: string;
  status?: string;
}

interface Transaction {
  rrn: string;
  status: string;
  cbs?: TransactionDetail;
  switch?: TransactionDetail;
  npci?: TransactionDetail;
  cbs_source?: string;
  switch_source?: string;
  npci_source?: string;
  suggested_action?: string;
  zero_difference?: boolean;
}

export default function ForceMatch() {
  const { toast } = useToast();
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [selectedTransaction, setSelectedTransaction] = useState<Transaction | null>(null);
  const [showDualPanelDialog, setShowDualPanelDialog] = useState(false);
  const [panelLHS, setPanelLHS] = useState<"cbs" | "switch" | "npci">("cbs");
  const [panelRHS, setPanelRHS] = useState<"cbs" | "switch" | "npci">("switch");
  const [isMatching, setIsMatching] = useState(false);
  const [zeroDifferenceValid, setZeroDifferenceValid] = useState(false);
  const [draggedPanel, setDraggedPanel] = useState<"cbs" | "switch" | "npci" | null>(null);
  const [expandedDetails, setExpandedDetails] = useState<{ [key: string]: boolean }>({});

  useEffect(() => {
    fetchUnmatchedTransactions();
  }, []);

  const fetchUnmatchedTransactions = async () => {
    try {
      setLoading(true);
      const rawData = await apiClient.getRawData();
      
      // Transform raw data to transaction format with detail objects
      const transformed: Transaction[] = Object.entries(rawData.data).map(([rrn, record]: [string, any]) => {
        const cbs = record.cbs ? {
          rrn: record.cbs.rrn || rrn,
          amount: record.cbs.amount || 0,
          date: record.cbs.date || '-',
          time: record.cbs.time,
          description: record.cbs.description,
          reference: record.cbs.reference,
          debit_credit: record.cbs.debit_credit
        } : undefined;

        const switchTxn = record.switch ? {
          rrn: record.switch.rrn || rrn,
          amount: record.switch.amount || 0,
          date: record.switch.date || '-',
          time: record.switch.time,
          description: record.switch.description,
          reference: record.switch.reference,
          debit_credit: record.switch.debit_credit
        } : undefined;

        const npci = record.npci ? {
          rrn: record.npci.rrn || rrn,
          amount: record.npci.amount || 0,
          date: record.npci.date || '-',
          time: record.npci.time,
          description: record.npci.description,
          reference: record.npci.reference,
          debit_credit: record.npci.debit_credit
        } : undefined;

        // Calculate zero-difference validation
        const amounts = [cbs?.amount, switchTxn?.amount, npci?.amount].filter(a => a !== undefined);
        const zeroDiff = amounts.length > 1 && amounts.every(a => a === amounts[0]);

        return {
          rrn,
          status: record.status,
          cbs,
          switch: switchTxn,
          npci,
          cbs_source: cbs ? 'X' : '',
          switch_source: switchTxn ? 'X' : '',
          npci_source: npci ? 'X' : '',
          suggested_action: getSuggestedAction(record),
          zero_difference: zeroDiff
        };
      });

      // Filter to show only unmatched/partial/orphan/mismatch transactions
      const unmatchedTransactions = transformed.filter(t => 
        ['PARTIAL_MATCH', 'ORPHAN', 'MISMATCH', 'PARTIAL_MISMATCH'].includes(t.status)
      );

      setTransactions(unmatchedTransactions);
    } catch (error: any) {
      console.error("Error fetching transactions:", error);
      toast({
        title: "Error",
        description: "Failed to load transactions. Please try again.",
        variant: "destructive"
      });
      setTransactions([]);
    } finally {
      setLoading(false);
    }
  };

  const getSuggestedAction = (record: any): string => {
    const status = record.status;
    if (status === 'ORPHAN') {
      const missing = [];
      if (!record.cbs) missing.push('CBS');
      if (!record.switch) missing.push('Switch');
      if (!record.npci) missing.push('NPCI');
      return `Investigate missing in ${missing.join(', ')}`;
    } else if (status === 'PARTIAL_MATCH') {
      const missing = [];
      if (!record.cbs) missing.push('CBS');
      if (!record.switch) missing.push('Switch');
      if (!record.npci) missing.push('NPCI');
      return `Check missing system data in ${missing.join(', ')}`;
    } else if (status === 'MISMATCH') {
      return 'CRITICAL: All systems have record but amounts/dates differ';
    } else if (status === 'PARTIAL_MISMATCH') {
      return 'WARNING: 2 systems have record but amounts/dates differ';
    }
    return 'Manual review required';
  };

  const handleOpenDualPanel = (transaction: Transaction) => {
    setSelectedTransaction(transaction);
    validateZeroDifference(transaction);
    setShowDualPanelDialog(true);
  };

  const validateZeroDifference = (transaction: Transaction) => {
    // Get amounts from selected panels
    const lhsAmount = transaction[panelLHS]?.amount;
    const rhsAmount = transaction[panelRHS]?.amount;
    
    if (lhsAmount !== undefined && rhsAmount !== undefined) {
      setZeroDifferenceValid(lhsAmount === rhsAmount);
    } else {
      setZeroDifferenceValid(false);
    }
  };

  const confirmForceMatch = async () => {
    if (!selectedTransaction) return;

    try {
      setIsMatching(true);

      if (!zeroDifferenceValid) {
        toast({
          title: "Warning",
          description: "Amounts do not match. Are you sure you want to proceed?",
          variant: "destructive"
        });
        return;
      }

      await apiClient.forceMatch(selectedTransaction.rrn, panelLHS, panelRHS, 'match');

      toast({
        title: "Success",
        description: `RRN ${selectedTransaction.rrn} has been force matched between ${panelLHS.toUpperCase()} (LHS) and ${panelRHS.toUpperCase()} (RHS)`,
      });

      // Refresh the data
      await fetchUnmatchedTransactions();
      setShowDualPanelDialog(false);
      setSelectedTransaction(null);
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.message || "Failed to force match. Please try again.",
        variant: "destructive"
      });
    } finally {
      setIsMatching(false);
    }
  };

  // Drag and Drop Handlers
  const handleDragStart = (e: React.DragEvent, panel: "cbs" | "switch" | "npci") => {
    setDraggedPanel(panel);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDrop = (e: React.DragEvent, targetPanel: "lhs" | "rhs") => {
    e.preventDefault();
    if (!draggedPanel) return;

    if (targetPanel === "lhs") {
      setPanelLHS(draggedPanel);
    } else {
      setPanelRHS(draggedPanel);
    }

    setDraggedPanel(null);
    validateZeroDifference(selectedTransaction!);
  };

  const toggleExpandedDetails = (panel: string) => {
    setExpandedDetails(prev => ({
      ...prev,
      [panel]: !prev[panel]
    }));
  };


  const getStatusBadge = (status: string) => {
    const variants: Record<string, { variant: "default" | "destructive" | "outline" | "secondary", color: string }> = {
      'MATCHED': { variant: 'default', color: 'bg-green-500' },
      'PARTIAL_MATCH': { variant: 'secondary', color: 'bg-yellow-500' },
      'ORPHAN': { variant: 'outline', color: 'bg-orange-500' },
      'MISMATCH': { variant: 'destructive', color: 'bg-red-500' },
      'PARTIAL_MISMATCH': { variant: 'destructive', color: 'bg-red-400' },
      'FORCE_MATCHED': { variant: 'default', color: 'bg-blue-500' }
    };

    const config = variants[status] || { variant: 'outline' as const, color: 'bg-gray-500' };
    
    return (
      <Badge variant={config.variant} className={`${config.color} text-white`}>
        {status.replace('_', ' ')}
      </Badge>
    );
  };

  const filteredTransactions = transactions.filter(t => {
    const matchesSearch = !searchTerm || t.rrn.includes(searchTerm);
    const matchesStatus = statusFilter === 'all' || t.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Force Match</h1>
          <p className="text-muted-foreground">Dual-panel transaction matching with zero-difference validation</p>
        </div>
        <Button 
          variant="outline" 
          size="sm" 
          onClick={fetchUnmatchedTransactions}
          disabled={loading}
          className="gap-2"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Info Alert */}
      <Alert className="border-blue-200 bg-blue-50">
        <ZoomIn className="h-4 w-4 text-blue-600" />
        <AlertTitle className="text-blue-900">Dual-Panel Matching</AlertTitle>
        <AlertDescription className="text-blue-800">
          Select two systems (LHS vs RHS) to compare amounts, dates, and references side-by-side. Zero-difference validation ensures perfect alignment before matching.
        </AlertDescription>
      </Alert>

      {/* Filters */}
      <Card className="shadow-lg">
        <CardContent className="pt-6">
          <div className="flex gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search by RRN..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
            <div className="w-64">
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="Filter by Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Statuses</SelectItem>
                  <SelectItem value="PARTIAL_MATCH">Partial Match</SelectItem>
                  <SelectItem value="ORPHAN">Orphan</SelectItem>
                  <SelectItem value="MISMATCH">Mismatch</SelectItem>
                  <SelectItem value="PARTIAL_MISMATCH">Partial Mismatch</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-foreground">
              {transactions.length}
            </div>
            <div className="text-sm text-muted-foreground">Total Unmatched</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-yellow-600">
              {transactions.filter(t => t.status === 'PARTIAL_MATCH').length}
            </div>
            <div className="text-sm text-muted-foreground">Partial Match</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-orange-600">
              {transactions.filter(t => t.status === 'ORPHAN').length}
            </div>
            <div className="text-sm text-muted-foreground">Orphan</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-red-600">
              {transactions.filter(t => t.status.includes('MISMATCH')).length}
            </div>
            <div className="text-sm text-muted-foreground">Mismatches</div>
          </CardContent>
        </Card>
      </div>

      {/* Transactions Table */}
      <Card className="shadow-lg">
        <CardHeader>
          <CardTitle>Transactions Requiring Attention</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="w-8 h-8 animate-spin text-brand-blue" />
            </div>
          ) : transactions.filter(t => {
            const matchesSearch = !searchTerm || t.rrn.includes(searchTerm);
            const matchesStatus = statusFilter === 'all' || t.status === statusFilter;
            return matchesSearch && matchesStatus;
          }).length === 0 ? (
            <div className="text-center py-8">
              <CheckCircle2 className="w-12 h-12 mx-auto text-green-500 mb-2" />
              <p className="text-muted-foreground">No unmatched transactions found</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>RRN</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-center">CBS</TableHead>
                    <TableHead className="text-center">Switch</TableHead>
                    <TableHead className="text-center">NPCI</TableHead>
                    <TableHead>CBS Amount</TableHead>
                    <TableHead>Switch Amount</TableHead>
                    <TableHead>NPCI Amount</TableHead>
                    <TableHead>Zero Diff</TableHead>
                    <TableHead className="text-right">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {transactions.filter(t => {
                    const matchesSearch = !searchTerm || t.rrn.includes(searchTerm);
                    const matchesStatus = statusFilter === 'all' || t.status === statusFilter;
                    return matchesSearch && matchesStatus;
                  }).map((transaction) => (
                    <TableRow key={transaction.rrn}>
                      <TableCell className="font-mono font-medium">{transaction.rrn}</TableCell>
                      <TableCell>{getStatusBadge(transaction.status)}</TableCell>
                      <TableCell className="text-center">
                        {transaction.cbs ? <CheckCircle2 className="w-4 h-4 text-green-500 mx-auto" /> : <AlertCircle className="w-4 h-4 text-red-500 mx-auto" />}
                      </TableCell>
                      <TableCell className="text-center">
                        {transaction.switch ? <CheckCircle2 className="w-4 h-4 text-green-500 mx-auto" /> : <AlertCircle className="w-4 h-4 text-red-500 mx-auto" />}
                      </TableCell>
                      <TableCell className="text-center">
                        {transaction.npci ? <CheckCircle2 className="w-4 h-4 text-green-500 mx-auto" /> : <AlertCircle className="w-4 h-4 text-red-500 mx-auto" />}
                      </TableCell>
                      <TableCell className="font-semibold">
                        {transaction.cbs ? `₹${transaction.cbs.amount.toLocaleString()}` : '-'}
                      </TableCell>
                      <TableCell className="font-semibold">
                        {transaction.switch ? `₹${transaction.switch.amount.toLocaleString()}` : '-'}
                      </TableCell>
                      <TableCell className="font-semibold">
                        {transaction.npci ? `₹${transaction.npci.amount.toLocaleString()}` : '-'}
                      </TableCell>
                      <TableCell>
                        {transaction.zero_difference ? (
                          <Badge className="bg-green-500 text-white">✓ Zero</Badge>
                        ) : (
                          <Badge variant="destructive">Has Variance</Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button 
                          size="sm" 
                          onClick={() => handleOpenDualPanel(transaction)}
                          className="rounded-full bg-brand-blue hover:bg-brand-mid gap-2"
                        >
                          <ZoomIn className="w-4 h-4" />
                          Open Panel
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Enhanced Dual-Panel Dialog */}
      <Dialog open={showDualPanelDialog} onOpenChange={setShowDualPanelDialog}>
        <DialogContent className="max-w-7xl max-h-[90vh] overflow-hidden">
          <DialogHeader className="pb-4">
            <DialogTitle className="flex items-center gap-3 text-xl">
              <div className="p-2 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg">
                <ZoomIn className="w-6 h-6 text-white" />
              </div>
              Dual-Panel Transaction Matcher
              <Badge variant="outline" className="ml-2 font-mono">
                {selectedTransaction?.rrn}
              </Badge>
            </DialogTitle>
            <DialogDescription className="text-base">
              Drag and drop systems to compare transaction details side-by-side with real-time zero-difference validation
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-6 py-4 max-h-[calc(90vh-200px)] overflow-y-auto">
            {/* Available Systems for Drag & Drop */}
            <div className="bg-gradient-to-r from-slate-50 to-slate-100 p-4 rounded-lg border">
              <h4 className="text-sm font-semibold mb-3 text-slate-700">Available Systems - Drag to Panels</h4>
              <div className="flex gap-3 flex-wrap">
                {selectedTransaction?.cbs && (
                  <div
                    draggable
                    onDragStart={(e) => handleDragStart(e, 'cbs')}
                    className="px-4 py-2 bg-blue-100 border-2 border-blue-300 rounded-lg cursor-move hover:bg-blue-200 transition-colors flex items-center gap-2"
                  >
                    <Hash className="w-4 h-4 text-blue-600" />
                    <span className="font-medium text-blue-800">CBS</span>
                  </div>
                )}
                {selectedTransaction?.switch && (
                  <div
                    draggable
                    onDragStart={(e) => handleDragStart(e, 'switch')}
                    className="px-4 py-2 bg-green-100 border-2 border-green-300 rounded-lg cursor-move hover:bg-green-200 transition-colors flex items-center gap-2"
                  >
                    <TrendingUp className="w-4 h-4 text-green-600" />
                    <span className="font-medium text-green-800">Switch</span>
                  </div>
                )}
                {selectedTransaction?.npci && (
                  <div
                    draggable
                    onDragStart={(e) => handleDragStart(e, 'npci')}
                    className="px-4 py-2 bg-purple-100 border-2 border-purple-300 rounded-lg cursor-move hover:bg-purple-200 transition-colors flex items-center gap-2"
                  >
                    <FileText className="w-4 h-4 text-purple-600" />
                    <span className="font-medium text-purple-800">NPCI</span>
                  </div>
                )}
              </div>
            </div>

            {/* Panel Selection with Drop Zones */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-start">
              {/* LHS Panel */}
              <div className="space-y-3">
                <label className="text-sm font-semibold text-center block text-slate-700">
                  LHS (Left Panel)
                  <span className="block text-xs text-slate-500 mt-1">Drop system here</span>
                </label>
                <div
                  onDragOver={handleDragOver}
                  onDrop={(e) => handleDrop(e, 'lhs')}
                  className={`min-h-[60px] border-2 border-dashed rounded-xl p-4 transition-all duration-300 ${
                    panelLHS
                      ? 'border-blue-400 bg-gradient-to-br from-blue-50 to-blue-100'
                      : 'border-slate-300 bg-slate-50 hover:border-slate-400'
                  }`}
                >
                  {panelLHS ? (
                    <div className="flex items-center justify-center gap-2">
                      <div className="p-2 bg-blue-500 rounded-lg">
                        {panelLHS === 'cbs' && <Hash className="w-4 h-4 text-white" />}
                        {panelLHS === 'switch' && <TrendingUp className="w-4 h-4 text-white" />}
                        {panelLHS === 'npci' && <FileText className="w-4 h-4 text-white" />}
                      </div>
                      <span className="font-semibold text-blue-800">{panelLHS.toUpperCase()}</span>
                    </div>
                  ) : (
                    <div className="text-center text-slate-500">
                      <ArrowRight className="w-6 h-6 mx-auto mb-1 opacity-50" />
                      <span className="text-xs">Drop system</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Comparison Indicator */}
              <div className="flex flex-col items-center justify-center space-y-4">
                <div className="w-full text-center">
                  <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full transition-all duration-500 ${
                    zeroDifferenceValid
                      ? 'bg-gradient-to-r from-green-100 to-emerald-100 border border-green-300'
                      : 'bg-gradient-to-r from-red-100 to-pink-100 border border-red-300'
                  }`}>
                    {zeroDifferenceValid ? (
                      <>
                        <CheckCircle2 className="w-5 h-5 text-green-600 animate-pulse" />
                        <span className="font-semibold text-green-800">Zero Difference</span>
                      </>
                    ) : (
                      <>
                        <AlertCircle className="w-5 h-5 text-red-600 animate-pulse" />
                        <span className="font-semibold text-red-800">Variance Found</span>
                      </>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2 text-slate-500">
                  <ArrowRight className="w-5 h-5" />
                  <span className="text-xs font-medium">Compare</span>
                  <ArrowRight className="w-5 h-5" />
                </div>
              </div>

              {/* RHS Panel */}
              <div className="space-y-3">
                <label className="text-sm font-semibold text-center block text-slate-700">
                  RHS (Right Panel)
                  <span className="block text-xs text-slate-500 mt-1">Drop system here</span>
                </label>
                <div
                  onDragOver={handleDragOver}
                  onDrop={(e) => handleDrop(e, 'rhs')}
                  className={`min-h-[60px] border-2 border-dashed rounded-xl p-4 transition-all duration-300 ${
                    panelRHS
                      ? 'border-green-400 bg-gradient-to-br from-green-50 to-green-100'
                      : 'border-slate-300 bg-slate-50 hover:border-slate-400'
                  }`}
                >
                  {panelRHS ? (
                    <div className="flex items-center justify-center gap-2">
                      <div className="p-2 bg-green-500 rounded-lg">
                        {panelRHS === 'cbs' && <Hash className="w-4 h-4 text-white" />}
                        {panelRHS === 'switch' && <TrendingUp className="w-4 h-4 text-white" />}
                        {panelRHS === 'npci' && <FileText className="w-4 h-4 text-white" />}
                      </div>
                      <span className="font-semibold text-green-800">{panelRHS.toUpperCase()}</span>
                    </div>
                  ) : (
                    <div className="text-center text-slate-500">
                      <ArrowLeft className="w-6 h-6 mx-auto mb-1 opacity-50" />
                      <span className="text-xs">Drop system</span>
                    </div>
                  )}
                </div>
              </div>
            </div>

            <Separator />

            {/* Enhanced Dual Panel Comparison */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* LHS Transaction Details */}
              <Card className="bg-gradient-to-br from-blue-50 to-indigo-50 border-blue-200 shadow-lg">
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg flex items-center gap-2 text-blue-900">
                    <div className="p-1 bg-blue-500 rounded">
                      {panelLHS === 'cbs' && <Hash className="w-4 h-4 text-white" />}
                      {panelLHS === 'switch' && <TrendingUp className="w-4 h-4 text-white" />}
                      {panelLHS === 'npci' && <FileText className="w-4 h-4 text-white" />}
                    </div>
                    {panelLHS?.toUpperCase()} Details
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Amount with enhanced styling */}
                  <div className="bg-white p-4 rounded-lg border border-blue-200">
                    <div className="flex items-center gap-2 mb-2">
                      <TrendingUp className="w-4 h-4 text-blue-600" />
                      <span className="text-sm font-medium text-blue-800">Amount</span>
                    </div>
                    <div className="text-2xl font-bold text-blue-900">
                      ₹{selectedTransaction?.[panelLHS]?.amount?.toLocaleString('en-IN', { minimumFractionDigits: 2 }) || '0.00'}
                    </div>
                  </div>

                  <Collapsible
                    open={expandedDetails[`lhs-${panelLHS}`]}
                    onOpenChange={() => toggleExpandedDetails(`lhs-${panelLHS}`)}
                  >
                    <CollapsibleTrigger asChild>
                      <Button variant="ghost" size="sm" className="w-full justify-between text-blue-700 hover:bg-blue-100">
                        Additional Details
                        {expandedDetails[`lhs-${panelLHS}`] ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </Button>
                    </CollapsibleTrigger>
                    <CollapsibleContent className="space-y-3 mt-3">
                      <div className="bg-white p-3 rounded border">
                        <div className="flex items-center gap-2 mb-1">
                          <Calendar className="w-4 h-4 text-blue-600" />
                          <span className="text-xs font-medium text-blue-800">Date</span>
                        </div>
                        <div className="font-semibold text-blue-900">{selectedTransaction?.[panelLHS]?.date || '-'}</div>
                      </div>

                      {selectedTransaction?.[panelLHS]?.time && (
                        <div className="bg-white p-3 rounded border">
                          <div className="flex items-center gap-2 mb-1">
                            <Clock className="w-4 h-4 text-blue-600" />
                            <span className="text-xs font-medium text-blue-800">Time</span>
                          </div>
                          <div className="font-semibold text-blue-900">{selectedTransaction?.[panelLHS]?.time}</div>
                        </div>
                      )}

                      {selectedTransaction?.[panelLHS]?.description && (
                        <div className="bg-white p-3 rounded border">
                          <div className="flex items-center gap-2 mb-1">
                            <FileText className="w-4 h-4 text-blue-600" />
                            <span className="text-xs font-medium text-blue-800">Description</span>
                          </div>
                          <div className="text-sm text-blue-900">{selectedTransaction?.[panelLHS]?.description}</div>
                        </div>
                      )}

                      {selectedTransaction?.[panelLHS]?.reference && (
                        <div className="bg-white p-3 rounded border">
                          <div className="flex items-center gap-2 mb-1">
                            <Hash className="w-4 h-4 text-blue-600" />
                            <span className="text-xs font-medium text-blue-800">Reference</span>
                          </div>
                          <div className="font-mono text-sm text-blue-900">{selectedTransaction?.[panelLHS]?.reference}</div>
                        </div>
                      )}
                    </CollapsibleContent>
                  </Collapsible>
                </CardContent>
              </Card>

              {/* Center Comparison */}
              <div className="hidden lg:flex flex-col items-center justify-center space-y-4">
                <div className="w-px h-32 bg-gradient-to-b from-blue-300 via-slate-300 to-green-300"></div>
                <div className="text-center">
                  <div className="text-sm font-medium text-slate-600">Comparison</div>
                  <div className="text-xs text-slate-500 mt-1">
                    {zeroDifferenceValid ? 'Amounts match perfectly' : 'Amounts differ - review carefully'}
                  </div>
                </div>
                <div className="w-px h-32 bg-gradient-to-b from-green-300 via-slate-300 to-blue-300"></div>
              </div>

              {/* RHS Transaction Details */}
              <Card className="bg-gradient-to-br from-green-50 to-emerald-50 border-green-200 shadow-lg">
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg flex items-center gap-2 text-green-900">
                    <div className="p-1 bg-green-500 rounded">
                      {panelRHS === 'cbs' && <Hash className="w-4 h-4 text-white" />}
                      {panelRHS === 'switch' && <TrendingUp className="w-4 h-4 text-white" />}
                      {panelRHS === 'npci' && <FileText className="w-4 h-4 text-white" />}
                    </div>
                    {panelRHS?.toUpperCase()} Details
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Amount with enhanced styling */}
                  <div className="bg-white p-4 rounded-lg border border-green-200">
                    <div className="flex items-center gap-2 mb-2">
                      <TrendingDown className="w-4 h-4 text-green-600" />
                      <span className="text-sm font-medium text-green-800">Amount</span>
                    </div>
                    <div className="text-2xl font-bold text-green-900">
                      ₹{selectedTransaction?.[panelRHS]?.amount?.toLocaleString('en-IN', { minimumFractionDigits: 2 }) || '0.00'}
                    </div>
                  </div>

                  <Collapsible
                    open={expandedDetails[`rhs-${panelRHS}`]}
                    onOpenChange={() => toggleExpandedDetails(`rhs-${panelRHS}`)}
                  >
                    <CollapsibleTrigger asChild>
                      <Button variant="ghost" size="sm" className="w-full justify-between text-green-700 hover:bg-green-100">
                        Additional Details
                        {expandedDetails[`rhs-${panelRHS}`] ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </Button>
                    </CollapsibleTrigger>
                    <CollapsibleContent className="space-y-3 mt-3">
                      <div className="bg-white p-3 rounded border">
                        <div className="flex items-center gap-2 mb-1">
                          <Calendar className="w-4 h-4 text-green-600" />
                          <span className="text-xs font-medium text-green-800">Date</span>
                        </div>
                        <div className="font-semibold text-green-900">{selectedTransaction?.[panelRHS]?.date || '-'}</div>
                      </div>

                      {selectedTransaction?.[panelRHS]?.time && (
                        <div className="bg-white p-3 rounded border">
                          <div className="flex items-center gap-2 mb-1">
                            <Clock className="w-4 h-4 text-green-600" />
                            <span className="text-xs font-medium text-green-800">Time</span>
                          </div>
                          <div className="font-semibold text-green-900">{selectedTransaction?.[panelRHS]?.time}</div>
                        </div>
                      )}

                      {selectedTransaction?.[panelRHS]?.description && (
                        <div className="bg-white p-3 rounded border">
                          <div className="flex items-center gap-2 mb-1">
                            <FileText className="w-4 h-4 text-green-600" />
                            <span className="text-xs font-medium text-green-800">Description</span>
                          </div>
                          <div className="text-sm text-green-900">{selectedTransaction?.[panelRHS]?.description}</div>
                        </div>
                      )}

                      {selectedTransaction?.[panelRHS]?.reference && (
                        <div className="bg-white p-3 rounded border">
                          <div className="flex items-center gap-2 mb-1">
                            <Hash className="w-4 h-4 text-green-600" />
                            <span className="text-xs font-medium text-green-800">Reference</span>
                          </div>
                          <div className="font-mono text-sm text-green-900">{selectedTransaction?.[panelRHS]?.reference}</div>
                        </div>
                      )}
                    </CollapsibleContent>
                  </Collapsible>
                </CardContent>
              </Card>
            </div>

            {/* Enhanced Warning/Validation */}
            {!zeroDifferenceValid && (
              <Alert variant="destructive" className="border-red-300 bg-gradient-to-r from-red-50 to-pink-50">
                <AlertCircle className="h-5 w-5 animate-pulse" />
                <AlertTitle className="text-red-800 font-semibold">Amount Mismatch Detected</AlertTitle>
                <AlertDescription className="text-red-700">
                  <div className="mt-2 space-y-1">
                    <div>LHS Amount: ₹{selectedTransaction?.[panelLHS]?.amount?.toLocaleString('en-IN', { minimumFractionDigits: 2 }) || '0.00'}</div>
                    <div>RHS Amount: ₹{selectedTransaction?.[panelRHS]?.amount?.toLocaleString('en-IN', { minimumFractionDigits: 2 }) || '0.00'}</div>
                    <div className="font-semibold mt-2">Please verify transaction details before proceeding with force match.</div>
                  </div>
                </AlertDescription>
              </Alert>
            )}

            {zeroDifferenceValid && (
              <Alert className="border-green-300 bg-gradient-to-r from-green-50 to-emerald-50">
                <CheckCircle2 className="h-5 w-5 text-green-600" />
                <AlertTitle className="text-green-800 font-semibold">Perfect Match Validated</AlertTitle>
                <AlertDescription className="text-green-700">
                  Amounts match exactly. Transaction details are ready for force matching.
                </AlertDescription>
              </Alert>
            )}
          </div>

          <DialogFooter className="border-t pt-4">
            <Button
              variant="outline"
              onClick={() => setShowDualPanelDialog(false)}
              disabled={isMatching}
              className="mr-2"
            >
              Cancel
            </Button>
            <Button
              onClick={confirmForceMatch}
              disabled={isMatching || panelLHS === panelRHS || !panelLHS || !panelRHS}
              className="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white shadow-lg"
            >
              {isMatching ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Processing Match...
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-4 h-4 mr-2" />
                  Confirm Force Match
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}