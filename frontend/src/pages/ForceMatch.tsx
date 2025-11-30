import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Input } from "../components/ui/input";
import { Button } from "../components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Badge } from "../components/ui/badge";
import { Loader2, CheckCircle2, AlertCircle, Search, RefreshCw } from "lucide-react";
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

interface Transaction {
  rrn: string;
  status: string;
  cbs_amount?: number;
  switch_amount?: number;
  npci_amount?: number;
  cbs_date?: string;
  switch_date?: string;
  npci_date?: string;
  cbs_source?: string;
  switch_source?: string;
  npci_source?: string;
  suggested_action?: string;
}

export default function ForceMatch() {
  const { toast } = useToast();
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [selectedTransaction, setSelectedTransaction] = useState<Transaction | null>(null);
  const [showMatchDialog, setShowMatchDialog] = useState(false);
  const [source1, setSource1] = useState<string>("cbs");
  const [source2, setSource2] = useState<string>("switch");
  const [isMatching, setIsMatching] = useState(false);

  useEffect(() => {
    fetchUnmatchedTransactions();
  }, []);

  const fetchUnmatchedTransactions = async () => {
    try {
      setLoading(true);
      const rawData = await apiClient.getRawData();
      
      // Transform raw data to transaction format
      const transformed: Transaction[] = Object.entries(rawData.data).map(([rrn, record]: [string, any]) => ({
        rrn,
        status: record.status,
        cbs_amount: record.cbs?.amount,
        switch_amount: record.switch?.amount,
        npci_amount: record.npci?.amount,
        cbs_date: record.cbs?.date,
        switch_date: record.switch?.date,
        npci_date: record.npci?.date,
        cbs_source: record.cbs ? 'X' : '',
        switch_source: record.switch ? 'X' : '',
        npci_source: record.npci ? 'X' : '',
        suggested_action: getSuggestedAction(record)
      }));

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

  const handleForceMatch = (transaction: Transaction) => {
    setSelectedTransaction(transaction);
    
    // Auto-select sources based on what's available
    const availableSources = [];
    if (transaction.cbs_source) availableSources.push('cbs');
    if (transaction.switch_source) availableSources.push('switch');
    if (transaction.npci_source) availableSources.push('npci');
    
    if (availableSources.length >= 2) {
      setSource1(availableSources[0]);
      setSource2(availableSources[1]);
    }
    
    setShowMatchDialog(true);
  };

  const confirmForceMatch = async () => {
    if (!selectedTransaction) return;

    try {
      setIsMatching(true);
      await apiClient.forceMatch(selectedTransaction.rrn, source1, source2, 'match');
      
      toast({
        title: "Success",
        description: `RRN ${selectedTransaction.rrn} has been force matched between ${source1.toUpperCase()} and ${source2.toUpperCase()}`,
      });

      // Refresh the data
      await fetchUnmatchedTransactions();
      setShowMatchDialog(false);
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
          <p className="text-muted-foreground">Manually match transactions between systems</p>
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
          ) : filteredTransactions.length === 0 ? (
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
                    <TableHead>Suggested Action</TableHead>
                    <TableHead className="text-right">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredTransactions.map((transaction) => (
                    <TableRow key={transaction.rrn}>
                      <TableCell className="font-mono font-medium">{transaction.rrn}</TableCell>
                      <TableCell>{getStatusBadge(transaction.status)}</TableCell>
                      <TableCell className="text-center">
                        {transaction.cbs_source && <CheckCircle2 className="w-4 h-4 text-green-500 mx-auto" />}
                        {!transaction.cbs_source && <AlertCircle className="w-4 h-4 text-red-500 mx-auto" />}
                      </TableCell>
                      <TableCell className="text-center">
                        {transaction.switch_source && <CheckCircle2 className="w-4 h-4 text-green-500 mx-auto" />}
                        {!transaction.switch_source && <AlertCircle className="w-4 h-4 text-red-500 mx-auto" />}
                      </TableCell>
                      <TableCell className="text-center">
                        {transaction.npci_source && <CheckCircle2 className="w-4 h-4 text-green-500 mx-auto" />}
                        {!transaction.npci_source && <AlertCircle className="w-4 h-4 text-red-500 mx-auto" />}
                      </TableCell>
                      <TableCell className="font-semibold">
                        {transaction.cbs_amount ? `₹${transaction.cbs_amount.toLocaleString()}` : '-'}
                      </TableCell>
                      <TableCell className="font-semibold">
                        {transaction.switch_amount ? `₹${transaction.switch_amount.toLocaleString()}` : '-'}
                      </TableCell>
                      <TableCell className="font-semibold">
                        {transaction.npci_amount ? `₹${transaction.npci_amount.toLocaleString()}` : '-'}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground max-w-xs">
                        {transaction.suggested_action}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button 
                          size="sm" 
                          onClick={() => handleForceMatch(transaction)}
                          className="rounded-full bg-brand-blue hover:bg-brand-mid"
                        >
                          Force Match
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

      {/* Force Match Dialog */}
      <Dialog open={showMatchDialog} onOpenChange={setShowMatchDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Force Match Transaction</DialogTitle>
            <DialogDescription>
              Select the two systems you want to force match for RRN: <strong>{selectedTransaction?.rrn}</strong>
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Source System 1</label>
              <Select value={source1} onValueChange={setSource1}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="cbs">CBS</SelectItem>
                  <SelectItem value="switch">Switch</SelectItem>
                  <SelectItem value="npci">NPCI</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Source System 2</label>
              <Select value={source2} onValueChange={setSource2}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="cbs">CBS</SelectItem>
                  <SelectItem value="switch">Switch</SelectItem>
                  <SelectItem value="npci">NPCI</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <p className="text-sm text-yellow-800">
                <strong>Warning:</strong> This will force match the transaction between {source1.toUpperCase()} and {source2.toUpperCase()}. 
                The data from {source1.toUpperCase()} will be used as the reference.
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button 
              variant="outline" 
              onClick={() => setShowMatchDialog(false)}
              disabled={isMatching}
            >
              Cancel
            </Button>
            <Button 
              onClick={confirmForceMatch}
              disabled={isMatching || source1 === source2}
              className="bg-brand-blue hover:bg-brand-mid"
            >
              {isMatching ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Matching...
                </>
              ) : (
                'Confirm Force Match'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}