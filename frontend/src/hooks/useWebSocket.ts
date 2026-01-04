import { useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import type { WSMessage } from '@/types';

interface UseWebSocketOptions {
  onMessage?: (message: WSMessage) => void;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

export function useWebSocket(url: string, options: UseWebSocketOptions = {}) {
  const {
    onMessage,
    reconnectInterval = 3000,
    maxReconnectAttempts = 5,
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WSMessage | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  const queryClient = useQueryClient();

  const connect = () => {
    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}${url}`;
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        reconnectAttemptsRef.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const message: WSMessage = JSON.parse(event.data);
          setLastMessage(message);

          // Handle different message types
          handleMessage(message);

          // Call custom message handler
          onMessage?.(message);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setIsConnected(false);

        // Attempt to reconnect
        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current++;
          console.log(
            `Reconnecting... (${reconnectAttemptsRef.current}/${maxReconnectAttempts})`
          );

          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, reconnectInterval);
        }
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
    }
  };

  const handleMessage = (message: WSMessage) => {
    switch (message.type) {
      case 'CAMPAIGN_UPDATE':
        if (message.campaign_id) {
          // Invalidate campaign queries to refetch data
          queryClient.invalidateQueries({ queryKey: ['campaigns'] });
          queryClient.invalidateQueries({
            queryKey: ['campaign', message.campaign_id],
          });
        }
        break;

      case 'TASK_COMPLETED':
      case 'TASK_FAILED':
        if (message.campaign_id) {
          // Invalidate campaign and tasks queries
          queryClient.invalidateQueries({
            queryKey: ['campaign', message.campaign_id],
          });
          queryClient.invalidateQueries({
            queryKey: ['campaign-tasks', message.campaign_id],
          });
        }
        break;

      case 'PROGRESS_UPDATE':
        if (message.campaign_id) {
          // Update progress without full refetch
          queryClient.setQueryData(
            ['campaign-status', message.campaign_id],
            message.data
          );
        }
        break;

      case 'AGENT_STATUS':
        if (message.agent_id) {
          queryClient.invalidateQueries({ queryKey: ['agents'] });
          queryClient.invalidateQueries({ queryKey: ['agent', message.agent_id] });
        }
        break;
    }
  };

  const sendMessage = (message: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket is not connected');
    }
  };

  const disconnect = () => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  };

  useEffect(() => {
    connect();

    return () => {
      disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url]);

  return {
    isConnected,
    lastMessage,
    sendMessage,
    disconnect,
  };
}

// Hook for campaign-specific WebSocket connection
export function useCampaignWebSocket(campaignId: string) {
  return useWebSocket(`/ws/campaigns/${campaignId}`);
}

// Hook for general updates WebSocket
export function useGeneralWebSocket() {
  return useWebSocket('/ws/updates');
}
