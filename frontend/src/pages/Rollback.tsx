import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Badge } from "../components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Loader2, RotateCcw, AlertTriangle, CheckCircle2, RefreshCw, Zap } from "lucide-react";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { Input } from "../components/ui/input";

interface RunHistory {
  run_id: string;
  date: string;
  time: string;
  total_transactions: number;
  matched: number;
  unmatched: number;
  status: string;
}

interface RollbackHistory {
  rollback_id: string;
  level: string;
  timestamp: string;
  status: string;
  details: any;
}

type RollbackLevel = "ingestion" | "mid_recon" | "cycle_wise" | "accounting";

export default function Rollback() {
  const { toast } = useToast();
  
  // State for run history
  const [runHistory, setRunHistory] = useState<RunHistory[]>([]);
  const [loading, setLoading] = useState(true);
  
  // State for granular rollback
  const [selectedRun, setSelectedRun] = useState<string>("");
  const [rollbackLevel, setRollbackLevel] = useState<RollbackLevel>("ingestion");
  const [failedFilename, setFailedFilename] = useState("");
  const [cycleId, setCycleId] = useState("");
  const [rollbackReason, setRollbackReason] = useState("");
  
  // UI state
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [isRollingBack, setIsRollingBack] = useState(false);
  const [rollbackHistory, setRollbackHistory] = useState<RollbackHistory[]>([]);
  const [rollbackHistoryLoading, setRollbackHistoryLoading] = useState(false);

  const NPCI_CYCLES = ['1C', '2C', '3C', '4C', '5C', '6C', '7C', '8C', '9C', '10C'];

  useEffect(() => {
    fetchRunHistory();
    fetchRollbackHistory();
  }, []);

  const fetchRunHistory = async () => {
    try {
      setLoading(true);
      
      const historical = await apiClient.getHistoricalSummary();
      
      const history: RunHistory[] = historical.map((item: any) => {
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

      try {
        const summary = await apiClient.getSummary();
        if (summary.run_id) {
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

  const fetchRollbackHistory = async () => {
    try {
      setRollbackHistoryLoading(true);
      const response = await fetch("/api/v1/rollback/history");
      if (response.ok) {
        const data = await response.json();
        setRollbackHistory(data.history || []);
      }
    } catch (error) {
      console.error("Error fetching rollback history:", error);
    } finally {
      setRollbackHistoryLoading(false);
    }
  };

  const handleRollback = async () => {
    if (!selectedRun) {
      toast({
        title: "Error",
        description: "Please select a run",
        variant: "destructive"
      });
      return;
    }

    try {
      setIsRollingBack(true);
      let response;

      switch (rollbackLevel) {
        case "ingestion":
          if (!failedFilename) {
            toast({
              title: "Error",
              description: "Please specify the failed filename",
              variant: "destructive"
            });
            return;
          }
          response = await fetch(
            `/api/v1/rollback/ingestion?run_id=${selectedRun}&filename=${failedFilename}&error=User initiated rollback`,
            { method: "POST" }
          );
          break;

        case "mid_recon":
          response = await fetch(
            `/api/v1/rollback/mid-recon?run_id=${selectedRun}&error=${encodeURIComponent(rollbackReason || "Critical error during reconciliation")}`,
            { method: "POST" }
          );
          break;

        case "cycle_wise":
          if (!cycleId) {
            toast({
              title: "Error",
              description: "Please select a cycle ID",
              variant: "destructive"
            });
            return;
          }
          response = await fetch(
            `/api/v1/rollback/cycle-wise?run_id=${selectedRun}&cycle_id=${cycleId}`,
            { method: "POST" }
          );
          break;

        case "accounting":
          response = await fetch(
            `/api/v1/rollback/accounting?run_id=${selectedRun}&reason=${encodeURIComponent(rollbackReason || "User initiated accounting rollback")}`,
            { method: "POST" }
          );
          break;

        default:
          throw new Error("Invalid rollback level");
      }

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Rollback failed");
      }

      const result = await response.json();

      toast({
        title: "Success",
        description: result.message || `${rollbackLevel} rollback completed successfully`,
      });

      setShowConfirmDialog(false);
      resetForm();
      await Promise.all([fetchRunHistory(), fetchRollbackHistory()]);
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.message || "Rollback failed. Please try again.",
        variant: "destructive"
      });
    } finally {
      setIsRollingBack(false);
    }
  };

  const resetForm = () => {
    setSelectedRun("");
    setFailedFilename("");
    setCycleId("");
    setRollbackReason("");
  };

  const getRollbackLevelBadge = (level: string) => {
    const colors: Record<string, string> = {
      ingestion: "bg-blue-500",
      mid_recon: "bg-orange-500",
      cycle_wise: "bg-purple-500",
      accounting: "bg-green-500"
    };
    
    return (
      <Badge className={`${colors[level] || "bg-gray-500"} text-white`}>
        {level.replace('_', ' ').toUpperCase()}
      </Badge>
    );
  };

  const getRollbackStatusBadge = (status: string) => {
    const variants: Record<string, any> = {
      'completed': { variant: 'default' as const, className: 'bg-green-500 text-white' },
      'in_progress': { variant: 'secondary' as const, className: 'bg-blue-500 text-white' },
      'failed': { variant: 'destructive' as const, className: 'bg-red-500 text-white' },
      'pending': { variant: 'outline' as const, className: 'bg-gray-500 text-white' }
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
          <h1 className="text-3xl font-bold text-foreground">Granular Rollback Manager</h1>
          <p className="text-muted-foreground">Phase 3: Undo operations at any stage with full control</p>
        </div>
        <Button 
          variant="outline" 
          size="sm" 
          onClick={() => Promise.all([fetchRunHistory(), fetchRollbackHistory()])}
          disabled={loading || rollbackHistoryLoading}
          className="gap-2"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="rollback" className="w-full">
        <TabsList className="bg-muted/30">
          <TabsTrigger value="rollback" className="data-[state=active]:bg-brand-blue data-[state=active]:text-primary-foreground">
            <Zap className="w-4 h-4 mr-2" />
            Granular Rollback
          </TabsTrigger>
          <TabsTrigger value="history" className="data-[state=active]:bg-brand-blue data-[state=active]:text-primary-foreground">
            <RotateCcw className="w-4 h-4 mr-2" />
            Rollback History
          </TabsTrigger>
          <TabsTrigger value="runs" className="data-[state=active]:bg-brand-blue data-[state=active]:text-primary-foreground">
            <RefreshCw className="w-4 h-4 mr-2" />
            Run History
          </TabsTrigger>
        </TabsList>

        {/* ROLLBACK TAB */}
        <TabsContent value="rollback" className="space-y-6 mt-6">
          {/* Warning Alert */}
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>Granular Rollback Operations</AlertTitle>
            <AlertDescription>
              Select the appropriate rollback level for your use case. Each level targets specific stages of the reconciliation process.
            </AlertDescription>
          </Alert>

          {/* Rollback Form */}
          <Card className="shadow-lg">
            <CardHeader>
              <CardTitle>Configure Rollback</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Run Selection */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Select Run</label>
                <Select value={selectedRun} onValueChange={setSelectedRun}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select a reconciliation run" />
                  </SelectTrigger>
                  <SelectContent>
                    {runHistory.map((run) => (
                      <SelectItem key={run.run_id} value={run.run_id}>
                        {run.run_id} - {run.date} {run.time} ({run.matched}/{run.total_transactions} matched)
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Rollback Level Selection */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Rollback Level</label>
                <div className="grid grid-cols-2 gap-3">
                  <Button
                    variant={rollbackLevel === "ingestion" ? "default" : "outline"}
                    className="h-24 flex flex-col items-center justify-center"
                    onClick={() => setRollbackLevel("ingestion")}
                  >
                    <div className="text-2xl mb-1">📁</div>
                    <div className="text-xs font-semibold">Ingestion</div>
                    <div className="text-xs text-muted-foreground">File validation</div>
                  </Button>
                  
                  <Button
                    variant={rollbackLevel === "mid_recon" ? "default" : "outline"}
                    className="h-24 flex flex-col items-center justify-center"
                    onClick={() => setRollbackLevel("mid_recon")}
                  >
                    <div className="text-2xl mb-1">⚡</div>
                    <div className="text-xs font-semibold">Mid-Recon</div>
                    <div className="text-xs text-muted-foreground">Critical error</div>
                  </Button>
                  
                  <Button
                    variant={rollbackLevel === "cycle_wise" ? "default" : "outline"}
                    className="h-24 flex flex-col items-center justify-center"
                    onClick={() => setRollbackLevel("cycle_wise")}
                  >
                    <div className="text-2xl mb-1">🔄</div>
                    <div className="text-xs font-semibold">Cycle-Wise</div>
                    <div className="text-xs text-muted-foreground">NPCI cycle</div>
                  </Button>
                  
                  <Button
                    variant={rollbackLevel === "accounting" ? "default" : "outline"}
                    className="h-24 flex flex-col items-center justify-center"
                    onClick={() => setRollbackLevel("accounting")}
                  >
                    <div className="text-2xl mb-1">📊</div>
                    <div className="text-xs font-semibold">Accounting</div>
                    <div className="text-xs text-muted-foreground">Voucher reset</div>
                  </Button>
                </div>
              </div>

              {/* Level-Specific Inputs */}
              {rollbackLevel === "ingestion" && (
                <div className="space-y-2">
                  <label className="text-sm font-medium">Failed Filename</label>
                  <Input 
                    placeholder="e.g., cbs_inward_20241204.csv"
                    value={failedFilename}
                    onChange={(e) => setFailedFilename(e.target.value)}
                  />
                </div>
              )}

              {rollbackLevel === "cycle_wise" && (
                <div className="space-y-2">
                  <label className="text-sm font-medium">NPCI Cycle ID</label>
                  <Select value={cycleId} onValueChange={setCycleId}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select NPCI cycle" />
                    </SelectTrigger>
                    <SelectContent>
                      {NPCI_CYCLES.map((cycle) => (
                        <SelectItem key={cycle} value={cycle}>
                          {cycle}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}

              {(rollbackLevel === "mid_recon" || rollbackLevel === "accounting") && (
                <div className="space-y-2">
                  <label className="text-sm font-medium">Reason for Rollback</label>
                  <Input 
                    placeholder="Provide reason for this rollback"
                    value={rollbackReason}
                    onChange={(e) => setRollbackReason(e.target.value)}
                  />
                </div>
              )}

              {/* Submit Button */}
              <Button 
                size="lg"
                className="w-full bg-brand-blue hover:bg-brand-mid"
                onClick={() => setShowConfirmDialog(true)}
                disabled={!selectedRun || isRollingBack}
              >
                {isRollingBack ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    <RotateCcw className="w-4 h-4 mr-2" />
                    Initiate Rollback
                  </>
                )}
              </Button>
            </CardContent>
          </Card>

          {/* Level Descriptions */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardContent className="pt-6 space-y-2">
                <h3 className="font-semibold flex items-center gap-2"><span>📁</span> Ingestion Rollback</h3>
                <p className="text-sm text-muted-foreground">
                  Removes a file that failed validation during upload. Other uploaded files are preserved.
                </p>
              </CardContent>
            </Card>
            
            <Card>
              <CardContent className="pt-6 space-y-2">
                <h3 className="font-semibold flex items-center gap-2"><span>⚡</span> Mid-Recon Rollback</h3>
                <p className="text-sm text-muted-foreground">
                  Restores uncommitted transactions after critical errors (DB crash, connection loss) back to unmatched state.
                </p>
              </CardContent>
            </Card>
            
            <Card>
              <CardContent className="pt-6 space-y-2">
                <h3 className="font-semibold flex items-center gap-2"><span>🔄</span> Cycle-Wise Rollback</h3>
                <p className="text-sm text-muted-foreground">
                  Rolls back a specific NPCI cycle (1A-1C, 2A-2C, 3A-3C, 4) for reprocessing without affecting others.
                </p>
              </CardContent>
            </Card>
            
            <Card>
              <CardContent className="pt-6 space-y-2">
                <h3 className="font-semibold flex items-center gap-2"><span>📊</span> Accounting Rollback</h3>
                <p className="text-sm text-muted-foreground">
                  Resets vouchers from settled state back to matched/pending when CBS upload fails.
                </p>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* HISTORY TAB */}
        <TabsContent value="history" className="space-y-6 mt-6">
          <Card className="shadow-lg">
            <CardHeader>
              <CardTitle>Rollback Operations History</CardTitle>
            </CardHeader>
            <CardContent>
              {rollbackHistoryLoading ? (
                <div className="flex justify-center py-8">
                  <Loader2 className="w-8 h-8 animate-spin text-brand-blue" />
                </div>
              ) : rollbackHistory.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-muted-foreground">No rollback operations found</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Rollback ID</TableHead>
                        <TableHead>Level</TableHead>
                        <TableHead>Run ID</TableHead>
                        <TableHead>Timestamp</TableHead>
                        <TableHead>Status</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {rollbackHistory.map((record) => (
                        <TableRow key={record.rollback_id}>
                          <TableCell className="font-mono text-xs">{record.rollback_id}</TableCell>
                          <TableCell>{getRollbackLevelBadge(record.level)}</TableCell>
                          <TableCell className="font-mono font-medium">{record.details.run_id || record.level}</TableCell>
                          <TableCell className="text-sm">{new Date(record.timestamp).toLocaleString()}</TableCell>
                          <TableCell>{getRollbackStatusBadge(record.status)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* RUNS TAB */}
        <TabsContent value="runs" className="space-y-6 mt-6">
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
                        <TableHead className="text-right">Total</TableHead>
                        <TableHead className="text-right">Matched</TableHead>
                        <TableHead className="text-right">Unmatched</TableHead>
                        <TableHead>Status</TableHead>
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
                          <TableCell>
                            <Badge className="bg-green-500 text-white">
                              {run.status.toUpperCase()}
                            </Badge>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Confirmation Dialog */}
      <AlertDialog open={showConfirmDialog} onOpenChange={setShowConfirmDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-orange-600" />
              Confirm {rollbackLevel.replace('_', ' ').toUpperCase()} Rollback
            </AlertDialogTitle>
            <AlertDialogDescription className="space-y-3">
              <p>
                Are you sure you want to perform a <strong>{rollbackLevel.replace('_', ' ')}</strong> rollback on <strong>{selectedRun}</strong>?
              </p>
              {rollbackLevel === "ingestion" && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                  <p className="text-sm text-blue-800">
                    File <strong>{failedFilename}</strong> will be removed from this run.
                  </p>
                </div>
              )}
              {rollbackLevel === "cycle_wise" && (
                <div className="bg-purple-50 border border-purple-200 rounded-lg p-3">
                  <p className="text-sm text-purple-800">
                    Cycle <strong>{cycleId}</strong> transactions will be restored to unmatched state for reprocessing.
                  </p>
                </div>
              )}
              {rollbackLevel === "mid_recon" && (
                <div className="bg-orange-50 border border-orange-200 rounded-lg p-3">
                  <p className="text-sm text-orange-800">
                    All uncommitted transactions will be restored to unmatched state.
                  </p>
                </div>
              )}
              {rollbackLevel === "accounting" && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                  <p className="text-sm text-green-800">
                    Vouchers will be reset from settled state to matched/pending.
                  </p>
                </div>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isRollingBack}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleRollback}
              disabled={isRollingBack}
              className="bg-orange-600 hover:bg-orange-700"
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