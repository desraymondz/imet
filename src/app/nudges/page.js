"use client";

import { useState, useEffect } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { useRouter } from 'next/navigation';

export default function NudgesPage() {
  const router = useRouter();
  const [nudges, setNudges] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [connections, setConnections] = useState([]);
  const [filter, setFilter] = useState('all'); // 'all', 'event', 'interest', 'followup'

  useEffect(() => {
    const fetchNudgesAndConnections = async () => {
      try {
        // Fetch connections first
        const connectionsResponse = await fetch('/api/connections');
        if (!connectionsResponse.ok) {
          throw new Error('Failed to fetch connections');
        }
        const connectionsData = await connectionsResponse.json();
        setConnections(connectionsData.connections);
        
        // Then fetch or generate nudges
        const nudgesResponse = await fetch('/api/nudges');
        if (nudgesResponse.ok) {
          const nudgesData = await nudgesResponse.json();
          setNudges(nudgesData.nudges);
        } else {
          // If no nudges API exists or returns error, generate sample nudges
          // In a real app, you would implement an actual AI-based nudge generation system
          const generatedNudges = generateSampleNudges(connectionsData.connections);
          setNudges(generatedNudges);
        }
      } catch (error) {
        console.error('Error fetching data:', error);
        setError('Failed to load recommendations');
        
        // Generate sample nudges even on error for demo purposes
        const sampleNudges = generateSampleNudges([]);
        setNudges(sampleNudges);
      } finally {
        setIsLoading(false);
      }
    };

    fetchNudgesAndConnections();
  }, []);

  // Generate sample nudges based on connections for demo
  // In a real app, this would be done server-side with actual AI processing
  const generateSampleNudges = (connections) => {
    const sampleNudges = [
      {
        id: '1',
        connectionId: connections[0]?.id || 'sample1',
        connectionName: connections[0]?.name || 'Arjun',
        type: 'event',
        title: "Today's Diwali — wish Arjun a good one.",
        description: "You met him at that sustainability event.",
        priority: 'high',
        action: 'message',
        dueDate: new Date().toISOString(),
      },
      {
        id: '2',
        connectionId: connections[1]?.id || 'sample2',
        connectionName: connections[1]?.name || 'Chris',
        type: 'interest',
        title: "You both love the Lakers — game night tonight.",
        description: "Want to text Chris?",
        priority: 'medium',
        action: 'message',
        dueDate: new Date().toISOString(),
      },
      {
        id: '3',
        connectionId: connections[2]?.id || 'sample3',
        connectionName: connections[2]?.name || 'Alisha',
        type: 'followup',
        title: "You said you'd check in with Alisha after her internship.",
        description: "That was 2 months ago. Time to follow up?",
        priority: 'low',
        action: 'call',
        dueDate: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
      },
      {
        id: '4',
        connectionId: connections[3]?.id || 'sample4',
        connectionName: connections[3]?.name || 'Maria',
        type: 'birthday',
        title: "Maria's birthday is tomorrow!",
        description: "Don't forget to send her a message.",
        priority: 'high',
        action: 'message',
        dueDate: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
      },
      {
        id: '5',
        connectionId: connections[4]?.id || 'sample5',
        connectionName: connections[4]?.name || 'Jordan',
        type: 'opportunity',
        title: "Jordan mentioned they're hiring at their company.",
        description: "Could be a good opportunity for your career switch.",
        priority: 'medium',
        action: 'email',
        dueDate: new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toISOString(),
      }
    ];
    
    return sampleNudges;
  };

  const filteredNudges = filter === 'all' 
    ? nudges 
    : nudges.filter(nudge => nudge.type === filter);

  const dismissNudge = (nudgeId) => {
    setNudges(nudges.filter(nudge => nudge.id !== nudgeId));
    // In a real app, you would also update this on the server
    // fetch(`/api/nudges/${nudgeId}`, { method: 'DELETE' });
  };

  const getActionIcon = (action) => {
    switch (action) {
      case 'message':
        return (
          <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
            <path d="M2 5a2 2 0 012-2h12a2 2 0 012 2v10a2 2 0 01-2 2H4a2 2 0 01-2-2V5zm3.293 1.293a1 1 0 011.414 0l3.5 3.5a1 1 0 010 1.414l-3.5 3.5a1 1 0 01-1.414-1.414L7.586 10 5.293 7.707a1 1 0 010-1.414zM11 12a1 1 0 100 2h3a1 1 0 100-2h-3z" />
          </svg>
        );
      case 'call':
        return (
          <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
            <path d="M2 3a1 1 0 011-1h2.153a1 1 0 01.986.836l.74 4.435a1 1 0 01-.54 1.06l-1.548.773a11.037 11.037 0 006.105 6.105l.774-1.548a1 1 0 011.059-.54l4.435.74a1 1 0 01.836.986V17a1 1 0 01-1 1h-2C7.82 18 2 12.18 2 5V3z" />
          </svg>
        );
      case 'email':
        return (
          <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
            <path d="M2.003 5.884L10 9.882l7.997-3.998A2 2 0 0016 4H4a2 2 0 00-1.997 1.884z" />
            <path d="M18 8.118l-8 4-8-4V14a2 2 0 002 2h12a2 2 0 002-2V8.118z" />
          </svg>
        );
      default:
        return (
          <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
          </svg>
        );
    }
  };

  const getPriorityClass = (priority) => {
    switch (priority) {
      case 'high':
        return 'bg-red-100 text-red-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'low':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const navigateToConnection = (connectionId) => {
    if (connectionId.startsWith('sample')) {
      // For sample connections, just redirect to the connections page
      router.push('/connections');
    } else {
      router.push(`/connections/${connectionId}`);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">Smart Social Nudges</h1>
        <button 
          onClick={() => setNudges(generateSampleNudges(connections))}
          className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg"
        >
          Refresh Nudges
        </button>
      </div>

      <div className="mb-6">
        <p className="text-gray-600">
          Smart recommendations to help you maintain and nurture your network. Never miss an important follow-up again.
        </p>
      </div>

      {/* Filter tabs */}
      <div className="flex space-x-2 border-b mb-6">
        <button 
          onClick={() => setFilter('all')}
          className={`px-4 py-2 ${filter === 'all' ? 'border-b-2 border-blue-500 text-blue-600' : 'text-gray-500'}`}
        >
          All
        </button>
        <button 
          onClick={() => setFilter('event')}
          className={`px-4 py-2 ${filter === 'event' ? 'border-b-2 border-blue-500 text-blue-600' : 'text-gray-500'}`}
        >
          Events
        </button>
        <button 
          onClick={() => setFilter('interest')}
          className={`px-4 py-2 ${filter === 'interest' ? 'border-b-2 border-blue-500 text-blue-600' : 'text-gray-500'}`}
        >
          Shared Interests
        </button>
        <button 
          onClick={() => setFilter('followup')}
          className={`px-4 py-2 ${filter === 'followup' ? 'border-b-2 border-blue-500 text-blue-600' : 'text-gray-500'}`}
        >
          Follow-ups
        </button>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
        </div>
      ) : error ? (
        <div className="bg-red-50 border-l-4 border-red-500 p-4 mb-4">
          <p className="text-red-700">{error}</p>
        </div>
      ) : filteredNudges.length > 0 ? (
        <div className="space-y-4">
          {filteredNudges.map((nudge) => (
            <div key={nudge.id} className="border rounded-lg shadow-sm p-4 bg-white">
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="flex items-center space-x-2 mb-2">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getPriorityClass(nudge.priority)}`}>
                      {nudge.priority.charAt(0).toUpperCase() + nudge.priority.slice(1)}
                    </span>
                    <span className="text-gray-500 text-sm">
                      {new Date(nudge.dueDate).toLocaleDateString()}
                    </span>
                  </div>
                  
                  <h3 className="text-lg font-semibold">{nudge.title}</h3>
                  <p className="text-gray-600 mt-1">{nudge.description}</p>
                  
                  <div className="mt-4 flex items-center space-x-4">
                    <button
                      onClick={() => navigateToConnection(nudge.connectionId)}
                      className="inline-flex items-center text-blue-600 hover:text-blue-800"
                    >
                      <span>View {nudge.connectionName}</span>
                      <svg className="h-4 w-4 ml-1" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
                      </svg>
                    </button>
                    
                    <div className="border-l pl-4 flex items-center space-x-2">
                      <span className="text-sm text-gray-500">Action:</span>
                      <button
                        className="inline-flex items-center rounded-full bg-blue-50 px-3 py-1 text-sm font-medium text-blue-700 hover:bg-blue-100"
                      >
                        {getActionIcon(nudge.action)}
                        <span className="ml-1 capitalize">{nudge.action}</span>
                      </button>
                    </div>
                  </div>
                </div>
                
                <button
                  onClick={() => dismissNudge(nudge.id)}
                  className="text-gray-400 hover:text-gray-500"
                >
                  <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                  </svg>
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-12">
          <p className="text-xl text-gray-500">No recommendations found.</p>
          <p className="mt-2">Add more connections to receive personalized nudges.</p>
          <Link 
            href="/memory-capture" 
            className="mt-4 inline-block px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg"
          >
            Add New Connection
          </Link>
        </div>
      )}
    </div>
  );
} 