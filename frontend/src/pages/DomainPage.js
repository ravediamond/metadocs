import React, { useState, useEffect, useContext } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { FileText, Settings, AlertCircle } from "lucide-react";
import { useParams, useNavigate } from 'react-router-dom';
import AuthContext from '../context/AuthContext';

const DomainPage = () => {
  const [domainData, setDomainData] = useState(null);
  const [error, setError] = useState(null);
  const { domain_id } = useParams();
  const { token, currentTenant } = useContext(AuthContext);

  const fetchData = async () => {
    try {
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/domains/tenants/${currentTenant}/domains/${domain_id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        setDomainData(data);
      } else {
        setError('Failed to fetch domain data');
      }
    } catch (error) {
      setError('Error fetching domain data');
      console.error('Error:', error);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const getMermaidDiagram = (data) => {
    if (!data?.ontology?.key) return null;
    return data.ontology.key;
  };

  const handleNavigate = (path) => {
    console.log('Navigate to:', path);
    // Replace with actual navigation logic
  };

  if (error) {
    return (
      <div className="p-4">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">
          {domainData?.domain_name || 'Domain Overview'}
        </h1>

        {domainData?.description && (
          <p className="text-gray-600 mb-6">{domainData.description}</p>
        )}

        <Card className="mb-8">
          <CardHeader>
            <CardTitle>Domain Diagram</CardTitle>
          </CardHeader>
          <CardContent>
            {getMermaidDiagram(domainData) ? (
              <div className="bg-white rounded-lg p-6 overflow-x-auto">
                <div className="mermaid">
                  {getMermaidDiagram(domainData)}
                </div>
              </div>
            ) : (
              <p className="text-gray-500 text-lg">No domain diagram available.</p>
            )}
          </CardContent>
        </Card>

        <div className="flex justify-center gap-4">
          <Button
            variant="outline"
            onClick={() => handleNavigate(`/domains/${domainData?.domain_id}/config`)}
            className="flex items-center gap-2"
          >
            <Settings className="h-4 w-4" />
            Domain Settings
          </Button>

          <Button
            onClick={() => handleNavigate(`/domains/${domainData?.domain_id}/files`)}
            className="flex items-center gap-2"
          >
            <FileText className="h-4 w-4" />
            Manage Files
          </Button>
        </div>

        {domainData?.last_processed_at && (
          <p className="text-sm text-gray-500 text-center mt-4">
            Last processed: {new Date(domainData.last_processed_at).toLocaleString()}
          </p>
        )}
      </div>
    </div>
  );
};

export default DomainPage;