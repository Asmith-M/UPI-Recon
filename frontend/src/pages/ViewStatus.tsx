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
      
      // Try to get upload metadata first to see which files were actually uploaded
      const metadata = await apiClient.getUploadMetadata();
      const uploadedFiles = metadata.uploaded_files || [];
      
      // Transform the uploaded files list into the status display
      const transformedData = transformRawDataToUploadStatus(uploadedFiles);
      setUploadStatusData(transformedData);
    } catch (error: any) {
      // If no metadata yet, show empty state with proper structure
      console.log("No upload metadata yet:", error.message);
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

  const transformRawDataToUploadStatus = (uploadedFiles: string[]) => {
    // Check which files were actually uploaded by looking at the uploaded_files array
    const has = (fileType: string) => uploadedFiles.includes(fileType) ? 1 : 0;

    return [
      {
        section: "CBS/ GL File",
        files: [
          { name: "CBS Inward File", required: 1, uploaded: has('cbs_inward'), success: has('cbs_inward'), error: 0 },
          { name: "CBS Outward File", required: 1, uploaded: has('cbs_outward'), success: has('cbs_outward'), error: 0 },
          { name: "Switch File", required: 1, uploaded: has('switch'), success: has('switch'), error: 0 },
        ],
      },
      {
        section: "NPCI Files",
        files: [
          { name: "NPCI Inward Raw", required: 1, uploaded: has('npci_inward'), success: has('npci_inward'), error: 0 },
          { name: "NPCI Outward Raw", required: 1, uploaded: has('npci_outward'), success: has('npci_outward'), error: 0 },
        ],
      },
      {
        section: "Other Files",
        files: [
          { name: "NTSL", required: 1, uploaded: has('ntsl'), success: has('ntsl'), error: 0 },
          { name: "Adjustment File", required: 0, uploaded: has('adjustment'), success: has('adjustment'), error: 0 },
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
                      <TableHead className="w-[40%]">File Name</TableHead>
                      <TableHead className="text-center w-[15%]">Required</TableHead>
                      <TableHead className="text-center w-[15%]">Uploaded</TableHead>
                      <TableHead className="text-center w-[15%]">Success</TableHead>
                      <TableHead className="text-center w-[15%]">Error</TableHead>
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
                          {file.success > 0 ? (
                            <div className="flex justify-center">
                              <Badge variant="default" className="bg-green-600 text-white">
                                {file.success}
                              </Badge>
                            </div>
                          ) : (
                            <span className="text-muted-foreground">-</span>
                          )}
                        </TableCell>
                        <TableCell className="text-center">
                          {file.error > 0 ? (
                            <div className="flex justify-center">
                              <Badge variant="destructive">{file.error}</Badge>
                            </div>
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