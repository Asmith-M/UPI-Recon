import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { AlertCircle, CheckCircle, Loader2 } from "lucide-react";
import { apiClient } from "../lib/api";
import { useToast } from "../hooks/use-toast";

export default function ViewStatus() {
  const { toast } = useToast();
  const [uploadStatusData, setUploadStatusData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedProcess, setSelectedProcess] = useState("inward");
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);

  useEffect(() => {
    fetchUploadStatus();
  }, []);

  const fetchUploadStatus = async () => {
    try {
      setLoading(true);
      
      // Try to get summary first to check if files are uploaded
      const summary = await apiClient.getSummary();
      
      // If we have summary data, files were successfully uploaded
      if (summary && summary.run_id) {
        const rawData = await apiClient.getRawData();
        const transformedData = transformRawDataToUploadStatus(rawData.data, true);
        setUploadStatusData(transformedData);
      } else {
        throw new Error("No data");
      }
    } catch (error: any) {
      // If no reconciliation data, show empty state with proper structure
      console.log("No reconciliation data yet or error:", error.message);
      setUploadStatusData([
        {
          section: "CBS/ GL File",
          files: [
            { name: "CBS Inward File", required: 1, uploaded: 0, success: 0, error: 0 },
            { name: "CBS Outward File", required: 1, uploaded: 0, success: 0, error: 0 },
            { name: "Switch File", required: 1, uploaded: 0, success: 0, error: 0 },
          ],
        },
        {
          section: "NPCI Files",
          files: [
            { name: "NPCI Inward Raw", required: 1, uploaded: 0, success: 0, error: 0 },
            { name: "NPCI Outward Raw", required: 1, uploaded: 0, success: 0, error: 0 },
          ],
        },
        {
          section: "Other Files",
          files: [
            { name: "NTSL", required: 1, uploaded: 0, success: 0, error: 0 },
            { name: "Adjustment File", required: 0, uploaded: 0, success: 0, error: 0 },
          ],
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const transformRawDataToUploadStatus = (rawData: any, hasData: boolean = false) => {
    // Check if we have actual data
    const hasRecords = rawData && Object.keys(rawData).length > 0;
    
    // Count records by checking if CBS/Switch/NPCI data exists in records
    let cbsCount = 0;
    let switchCount = 0;
    let npciCount = 0;
    
    if (hasRecords) {
      Object.values(rawData).forEach((record: any) => {
        if (record.cbs) cbsCount++;
        if (record.switch) switchCount++;
        if (record.npci) npciCount++;
      });
    }

    return [
      {
        section: "CBS/ GL File",
        files: [
          { name: "CBS Inward File", required: 1, uploaded: hasData ? 1 : 0, success: cbsCount > 0 ? 1 : 0, error: 0 },
          { name: "CBS Outward File", required: 1, uploaded: hasData ? 1 : 0, success: cbsCount > 0 ? 1 : 0, error: 0 },
          { name: "Switch File", required: 1, uploaded: hasData ? 1 : 0, success: switchCount > 0 ? 1 : 0, error: 0 },
        ],
      },
      {
        section: "NPCI Files",
        files: [
          { name: "NPCI Inward Raw", required: 1, uploaded: hasData ? 1 : 0, success: npciCount > 0 ? 1 : 0, error: 0 },
          { name: "NPCI Outward Raw", required: 1, uploaded: hasData ? 1 : 0, success: npciCount > 0 ? 1 : 0, error: 0 },
        ],
      },
      {
        section: "Other Files",
        files: [
          { name: "NTSL", required: 1, uploaded: hasData ? 1 : 0, success: hasData ? 1 : 0, error: 0 },
          { name: "Adjustment File", required: 0, uploaded: hasData ? 1 : 0, success: hasData ? 1 : 0, error: 0 },
        ],
      },
    ];
  };
  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">View Upload Status</h1>
        <p className="text-muted-foreground">Check the status of your file uploads</p>
      </div>

      {/* Filter Section */}
      <Card className="shadow-lg">
        <CardContent className="pt-6">
          <div className="flex gap-4 items-end">
            <div className="flex-1 space-y-2">
              <Label>Process</Label>
              <Select value={selectedProcess} onValueChange={setSelectedProcess}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="inward">Inward</SelectItem>
                  <SelectItem value="outward">Outward</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div className="flex-1 space-y-2">
              <Label>Date:</Label>
              <Input
                type="date"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">(Default Set to 'T' Day)</p>
            </div>

            <Button 
              className="rounded-full px-8 bg-brand-blue hover:bg-brand-mid"
              onClick={fetchUploadStatus}
              disabled={loading}
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Refreshing...
                </>
              ) : (
                "Refresh Status"
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Overall Status */}
      <div className="grid grid-cols-3 gap-6">
        <Card className={`shadow-lg ${uploadStatusData[0]?.files.some(f => f.success > 0) ? 'bg-gradient-to-br from-green-50 to-card' : 'bg-gradient-to-br from-red-50 to-card'}`}>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">CBS/ GL File</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              {uploadStatusData[0]?.files.some(f => f.success > 0) ? (
                <>
                  <CheckCircle className="w-5 h-5 text-green-600" />
                  <span className="text-lg font-semibold text-green-600">Successful</span>
                </>
              ) : (
                <>
                  <AlertCircle className="w-5 h-5 text-red-600" />
                  <span className="text-lg font-semibold text-red-600">Not Uploaded</span>
                </>
              )}
            </div>
          </CardContent>
        </Card>

        <Card className={`shadow-lg ${uploadStatusData[0]?.files[2]?.success > 0 ? 'bg-gradient-to-br from-green-50 to-card' : 'bg-gradient-to-br from-red-50 to-card'}`}>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">Switch</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              {uploadStatusData[0]?.files[2]?.success > 0 ? (
                <>
                  <CheckCircle className="w-5 h-5 text-green-600" />
                  <span className="text-lg font-semibold text-green-600">Successful</span>
                </>
              ) : (
                <>
                  <AlertCircle className="w-5 h-5 text-red-600" />
                  <span className="text-lg font-semibold text-red-600">Not Uploaded</span>
                </>
              )}
            </div>
          </CardContent>
        </Card>

        <Card className={`shadow-lg ${uploadStatusData[1]?.files.some(f => f.success > 0) ? 'bg-gradient-to-br from-green-50 to-card' : 'bg-gradient-to-br from-red-50 to-card'}`}>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">NPCI Files</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              {uploadStatusData[1]?.files.some(f => f.success > 0) ? (
                <>
                  <CheckCircle className="w-5 h-5 text-green-600" />
                  <span className="text-lg font-semibold text-green-600">Successful</span>
                </>
              ) : (
                <>
                  <AlertCircle className="w-5 h-5 text-red-600" />
                  <span className="text-lg font-semibold text-red-600">Not Uploaded</span>
                </>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Detailed Table */}
      <Card className="shadow-lg">
        <CardHeader>
          <CardTitle>File Upload Details</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            {uploadStatusData.map((section, idx) => (
              <div key={idx} className="space-y-3">
                <h3 className="font-semibold text-brand-blue">{section.section}</h3>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>File Name</TableHead>
                      <TableHead className="text-center">Required</TableHead>
                      <TableHead className="text-center">Uploaded</TableHead>
                      <TableHead className="text-center">Success</TableHead>
                      <TableHead className="text-center">Error</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {section.files.map((file, fileIdx) => (
                      <TableRow key={fileIdx}>
                        <TableCell className="font-medium">{file.name}</TableCell>
                        <TableCell className="text-center">
                          {file.required === 0 ? "NA" : file.required}
                        </TableCell>
                        <TableCell className="text-center">{file.uploaded}</TableCell>
                        <TableCell className="text-center">
                          <Badge variant={file.success > 0 ? "default" : "secondary"} className="bg-green-600">
                            {file.success}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-center">
                          {file.error > 0 ? (
                            <Badge variant="destructive">{file.error}</Badge>
                          ) : (
                            <span className="text-muted-foreground">-</span>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
              ))}
            </div>
        </CardContent>
      </Card>
    </div>
  );
}