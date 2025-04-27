import React from 'react';import React from 'react';





































































};  );    </Grid>      <ConfidenceLevels levels={data.confidence_levels} />      <CategoryScores scores={data.category_scores} />      <AnalysisChart data={data} />    <Grid templateColumns="repeat(2, 1fr)" gap={6}>  return (    );      </Box>        <Heading size="md">No data available for {symbol}</Heading>      <Box textAlign="center" py={10}>    return (  if (!data)    );      </Alert>        <Box mt={2}>{(error as Error).message}</Box>        <Heading size="md">Error</Heading>        <AlertIcon />      <Alert status="error" variant="subtle" flexDirection="column" alignItems="center" justifyContent="center" textAlign="center" height="200px">    return (  if (error)    );      </Box>        </Heading>          Loading analysis for {symbol}...        <Heading size="md" mt={4}>        <Spinner size="xl" />      <Box textAlign="center" py={10}>    return (  if (isLoading)  );    }      },        });          isClosable: true,          duration: 5000,          status: 'error',          description: err.message,          title: 'Error',        toast({      onError: (err: Error) => {    {    },      return response.json();      if (!response.ok) throw new Error('Failed to fetch analysis data');      const response = await fetch(`/api/analyze/${symbol}`);    async () => {    ['analysis', symbol],  const { data, isLoading, error } = useQuery<AnalysisResult>(  const toast = useToast();export const AnalysisDashboard: React.FC<{ symbol: string }> = ({ symbol }) => {}  metadata: any;  confidence_levels: Record<string, number>;  category_scores: Record<string, number>;  score: number;interface AnalysisResult {import { ConfidenceLevels } from './ConfidenceLevels';import { CategoryScores } from './CategoryScores';import { AnalysisChart } from './AnalysisChart';import { useQuery } from 'react-query';import { Box, Grid, Heading, Spinner, Alert, AlertIcon, useToast } from '@chakra-ui/react';import { Box, Grid, Heading, Spinner, Alert, AlertIcon, useToast } from '@chakra-ui/react';
import { useQuery } from 'react-query';
import { AnalysisChart } from './AnalysisChart';
import { CategoryScores } from './CategoryScores';
import { ConfidenceLevels } from './ConfidenceLevels';

interface AnalysisResult {
  score: number;
  category_scores: Record<string, number>;
  confidence_levels: Record<string, number>;
  metadata: any;
}

export const AnalysisDashboard: React.FC<{ symbol: string }> = ({ symbol }) => {
  const toast = useToast();
  const { data, isLoading, error } = useQuery<AnalysisResult>(
    ['analysis', symbol],
    async () => {
      const response = await fetch(`/api/analyze/${symbol}`);
      if (!response.ok) throw new Error('Failed to fetch analysis data');
      return response.json();
    },
    {
      onError: (err: Error) => {
        toast({
          title: 'Error',
          description: err.message,
          status: 'error',
          duration: 5000,
          isClosable: true,
        });
      },
    }
  );

  if (isLoading)
    return (
      <Box textAlign="center" py={10}>
        <Spinner size="xl" />
        <Heading size="md" mt={4}>
          Loading analysis for {symbol}...
        </Heading>
      </Box>
    );

  if (error)
    return (
      <Alert status="error" variant="subtle" flexDirection="column" alignItems="center" justifyContent="center" textAlign="center" height="200px">
        <AlertIcon />
        <Heading size="md">Error</Heading>
        <Box mt={2}>{(error as Error).message}</Box>
      </Alert>
    );

  if (!data)
    return (
      <Box textAlign="center" py={10}>
        <Heading size="md">No data available for {symbol}</Heading>
      </Box>
    );

  return (
    <Grid templateColumns="repeat(2, 1fr)" gap={6}>
      <AnalysisChart data={data} />
      <CategoryScores scores={data.category_scores} />
      <ConfidenceLevels levels={data.confidence_levels} />
    </Grid>
  );
};
