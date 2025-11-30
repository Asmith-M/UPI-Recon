import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Badge } from "../components/ui/badge";
import { Loader2, RotateCcw, AlertTriangle, CheckCircle2, RefreshCw } from "lucide-react";
import { useToast } from "../hooks/use-toast";
import { apiClient } from "../lib/api";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "../components/ui/alert-dialog";
import {
  Alert,
  AlertDescription,
  AlertTitle,
} from "../components/ui/alert";

interface RunHistory {
  run_id: string;
  date: string;
  time: string;
  total_transactions: number;
  matched: number;
  unmatched: number;
  status: string;
}

export default function Rollback() {
  const { toast } = useToast();
  const [runHistory, setRunHistory] = useState<RunHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedRun, setSelectedRun] = useState<string | null>(null);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [isRollingBack, setIsRollingBack] = useState(false);

  useEffect(() => {
    fetchRunHistory();
  }, []);

  const fetchRunHistory = async () => {
    try {
      setLoading(true);
      
      // Fetch historical summary to get run history
      const historical = await apiClient.getHistoricalSummary();
      
      // Transform to run history format
      const history: RunHistory[] = historical.map((item: any) => {
        // Extract date and time from month format or use mock data
        const runId = `RUN_${item.month.replace('-', '')}`;
        return {
          run_id: runId,
          date: `2024-${item.month}`,
          time: '12:00:00',
          total_transactions: item.allTxns || 0,
          matched: item.reconciled || 0,
          unmatched: (item.allTxns || 0) - (item.reconciled || 0),
          status: 'completed'
        };
      });

      // Try to get the latest run for more accurate data
      try {
        const summary = await apiClient.getSummary();
        if (summary.run_id) {
          // Parse run_id format: RUN_YYYYMMDD_HHMMSS
          const runIdParts = summary.run_id.split('_');
          if (runIdParts.length >= 3) {
            const dateStr = runIdParts[1];
            const timeStr = runIdParts[2];
            
            const latestRun: RunHistory = {
              run_id: summary.run_id,
              date: `${dateStr.substring(0, 4)}-${dateStr.substring(4, 6)}-${dateStr.substring(6, 8)}`,
              time: `${timeStr.substring(0, 2)}:${timeStr.substring(2, 4)}:${timeStr.substring(4, 6)}`,
              total_transactions: summary.total_transactions,
              matched: summary.matched,
              unmatched: summary.unmatched,
              status: summary.status
            };
            
            // Add to beginning if not already present
            const exists = history.some(h => h.run_id === summary.run_id);
            if (!exists) {
              history.unshift(latestRun);
            }
          }
        }
      } catch (error) {
        console.log("Could not fetch latest run details");
      }

      setRunHistory(history);
    } catch (error: any) {
      console.error("Error fetching run history:", error);
      toast({
        title: "Error",
        description: "Failed to load run history. Please try again.",
        variant: "destructive"
      });
      setRunHistory([]);
    } finally {
      setLoading(false);
    }
  };

  const handleRollbackClick = (runId: string) => {
    setSelectedRun(runId);
    setShowConfirmDialog(true);
  };

  const confirmRollback = async () => {
    if (!selectedRun) return;

    try {
      setIsRollingBack(true);
      
      await apiClient.rollbackReconciliation(selectedRun);
      
      toast({
        title: "Success",
        description: `Reconciliation run ${selectedRun} has been rolled back successfully`,
      });

      // Refresh the run history
      await fetchRunHistory();
      setShowConfirmDialog(false);
      setSelectedRun(null);
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.message || "Failed to rollback. Please try again.",
        variant: "destructive"
      });
    } finally {
      setIsRollingBack(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, { variant: "default" | "destructive" | "outline" | "secondary", className: string }> = {
      'completed': { variant: 'default', className: 'bg-green-500 text-white' },
      'running': { variant: 'secondary', className: 'bg-blue-500 text-white' },
      'failed': { variant: 'destructive', className: 'bg-red-500 text-white' },
      'rolled_back': { variant: 'outline', className: 'bg-gray-500 text-white' }
    };

    const config = variants[status] || { variant: 'outline' as const, className: 'bg-gray-500 text-white' };
    
    return (
      <Badge variant={config.variant} className={config.className}>
        {status.replace('_', ' ').toUpperCase()}
      </Badge>
    );
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Rollback Reconciliation</h1>
          <p className="text-muted-foreground">Undo reconciliation runs and restore previous state</p>
        </div>
        <Button 
          variant="outline" 
          size="sm" 
          onClick={fetchRunHistory}
          disabled={loading}
          className="gap-2"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Warning Alert */}
      <Alert variant="destructive">
        <AlertTriangle className="h-4 w-4" />
        <AlertTitle>Warning</AlertTitle>
        <AlertDescription>
          Rolling back a reconciliation run will permanently delete all reconciliation data for that run.
          This action cannot be undone. Please ensure you have backups before proceeding.
        </AlertDescription>
      </Alert>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-blue-100 rounded-full">
                <RotateCcw className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <div className="text-2xl font-bold text-foreground">
                  {runHistory.length}
                </div>
                <div className="text-sm text-muted-foreground">Total Runs</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-green-100 rounded-full">
                <CheckCircle2 className="w-6 h-6 text-green-600" />
              </div>
              <div>
                <div className="text-2xl font-bold text-green-600">
                  {runHistory.filter(r => r.status === 'completed').length}
                </div>
                <div className="text-sm text-muted-foreground">Completed</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-red-100 rounded-full">
                <AlertTriangle className="w-6 h-6 text-red-600" />
              </div>
              <div>
                <div className="text-2xl font-bold text-red-600">
                  {runHistory.filter(r => r.status === 'failed').length}
                </div>
                <div className="text-sm text-muted-foreground">Failed</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Run History Table */}
      <Card className="shadow-lg">
        <CardHeader>
          <CardTitle>Reconciliation Run History</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="w-8 h-8 animate-spin text-brand-blue" />
            </div>
          ) : runHistory.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-muted-foreground">No reconciliation runs found</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Run ID</TableHead>
                    <TableHead>Date</TableHead>
                    <TableHead>Time</TableHead>
                    <TableHead className="text-right">Total Transactions</TableHead>
                    <TableHead className="text-right">Matched</TableHead>
                    <TableHead className="text-right">Unmatched</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {runHistory.map((run) => (
                    <TableRow key={run.run_id}>
                      <TableCell className="font-mono font-medium">{run.run_id}</TableCell>
                      <TableCell>{run.date}</TableCell>
                      <TableCell>{run.time}</TableCell>
                      <TableCell className="text-right font-semibold">
                        {run.total_transactions.toLocaleString()}
                      </TableCell>
                      <TableCell className="text-right text-green-600 font-semibold">
                        {run.matched.toLocaleString()}
                      </TableCell>
                      <TableCell className="text-right text-red-600 font-semibold">
                        {run.unmatched.toLocaleString()}
                      </TableCell>
                      <TableCell>{getStatusBadge(run.status)}</TableCell>
                      <TableCell className="text-right">
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => handleRollbackClick(run.run_id)}
                          disabled={run.status === 'rolled_back'}
                          className="gap-2"
                        >
                          <RotateCcw className="w-4 h-4" />
                          Rollback
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

      {/* Confirmation Dialog */}
      <AlertDialog open={showConfirmDialog} onOpenChange={setShowConfirmDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-red-600" />
              Confirm Rollback
            </AlertDialogTitle>
            <AlertDialogDescription className="space-y-3">
              <p>
                Are you sure you want to rollback the reconciliation run <strong>{selectedRun}</strong>?
              </p>
              <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                <p className="text-sm text-red-800">
                  <strong>Warning:</strong> This action will:
                </p>
                <ul className="text-sm text-red-800 list-disc list-inside mt-2 space-y-1">
                  <li>Delete all reconciliation data for this run</li>
                  <li>Remove generated reports and adjustments</li>
                  <li>Cannot be undone</li>
                </ul>
              </div>
              <p className="text-sm">
                Please ensure you have backed up any important data before proceeding.
              </p>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isRollingBack}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmRollback}
              disabled={isRollingBack}
              className="bg-red-600 hover:bg-red-700"
            >
              {isRollingBack ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Rolling Back...
                </>
              ) : (
                <>
                  <RotateCcw className="w-4 h-4 mr-2" />
                  Confirm Rollback
                </>
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}