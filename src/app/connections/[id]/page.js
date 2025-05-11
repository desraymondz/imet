"use client";

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Image from 'next/image';
import Link from 'next/link';

export default function ConnectionDetailPage() {
  const router = useRouter();
  const params = useParams();
  const { id } = params;
  
  const [connection, setConnection] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Fetch the specific connection
    const fetchConnection = async () => {
      try {
        const response = await fetch(`/api/connections/${id}`);
        if (response.ok) {
          const data = await response.json();
          setConnection(data.connection);
        } else {
          setError('Failed to fetch connection details');
        }
      } catch (error) {
        console.error('Error fetching connection:', error);
        setError('An error occurred while fetching the connection');
      } finally {
        setIsLoading(false);
      }
    };

    if (id) {
      fetchConnection();
    }
  }, [id]);

  const handleDelete = async () => {
    if (confirm('Are you sure you want to delete this connection?')) {
      try {
        const response = await fetch(`/api/connections/${id}`, {
          method: 'DELETE',
        });
        
        if (response.ok) {
          router.push('/connections');
        } else {
          setError('Failed to delete connection');
        }
      } catch (error) {
        console.error('Error deleting connection:', error);
        setError('An error occurred while deleting the connection');
      }
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error || !connection) {
    return (
      <div className="max-w-4xl mx-auto p-6 text-center">
        <h1 className="text-2xl font-bold text-red-500 mb-4">Error</h1>
        <p>{error || 'Connection not found'}</p>
        <Link 
          href="/connections" 
          className="inline-block mt-6 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg"
        >
          Back to Connections
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="flex justify-between items-center mb-8">
        <Link 
          href="/connections" 
          className="text-blue-500 hover:underline flex items-center"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-1" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" clipRule="evenodd" />
          </svg>
          Back to Connections
        </Link>

        <div className="flex space-x-3">
          <Link 
            href={`/connections/edit/${id}`} 
            className="px-4 py-2 bg-gray-200 hover:bg-gray-300 text-gray-800 rounded-lg"
          >
            Edit
          </Link>
          <button 
            onClick={handleDelete}
            className="px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg"
          >
            Delete
          </button>
        </div>
      </div>

      <div className="bg-white rounded-lg overflow-hidden shadow-lg">
        {/* Header with image and name */}
        <div className="relative">
          {connection.image ? (
            <Image
              src={connection.image}
              alt={connection.name || 'Connection'}
              width={1200}
              height={400}
              className="w-full h-64 object-cover"
            />
          ) : (
            <div className="w-full h-64 bg-gradient-to-r from-blue-100 to-blue-200 flex items-center justify-center">
              <span className="text-8xl font-bold text-blue-500">
                {connection.name ? connection.name.charAt(0).toUpperCase() : '?'}
              </span>
            </div>
          )}
        </div>

        <div className="p-8">
          <h1 className="text-3xl font-bold mb-6">{connection.name || 'Unnamed Connection'}</h1>
          
          {/* Tags */}
          {connection.tags && connection.tags.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-6">
              {connection.tags.map(tag => (
                <span 
                  key={tag} 
                  className="inline-block px-3 py-1 bg-gray-100 text-gray-800 text-sm rounded-full"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* Left column */}
            <div className="space-y-6">
              {/* Meeting Details */}
              {(connection.meetingLocation || connection.meetingDate) && (
                <div>
                  <h2 className="text-xl font-semibold border-b pb-2 mb-3">Where & When We Met</h2>
                  {connection.meetingLocation && (
                    <p className="mb-1">
                      <span className="font-medium">Location:</span> {connection.meetingLocation}
                    </p>
                  )}
                  {connection.meetingDate && (
                    <p>
                      <span className="font-medium">Date:</span> {connection.meetingDate}
                    </p>
                  )}
                </div>
              )}
              
              {/* Interests */}
              {connection.interests && connection.interests.length > 0 && (
                <div>
                  <h2 className="text-xl font-semibold border-b pb-2 mb-3">Interests & Goals</h2>
                  <ul className="list-disc pl-5 space-y-1">
                    {connection.interests.map((interest, index) => (
                      <li key={index}>{interest}</li>
                    ))}
                  </ul>
                </div>
              )}
              
              {/* Contact Info */}
              {(connection.email || connection.phone || connection.linkedin) && (
                <div>
                  <h2 className="text-xl font-semibold border-b pb-2 mb-3">Contact Information</h2>
                  {connection.email && (
                    <p className="mb-1">
                      <span className="font-medium">Email:</span> {connection.email}
                    </p>
                  )}
                  {connection.phone && (
                    <p className="mb-1">
                      <span className="font-medium">Phone:</span> {connection.phone}
                    </p>
                  )}
                  {connection.linkedin && (
                    <p>
                      <span className="font-medium">LinkedIn:</span>{' '}
                      <a 
                        href={connection.linkedin} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="text-blue-500 hover:underline"
                      >
                        {connection.linkedin}
                      </a>
                    </p>
                  )}
                </div>
              )}
            </div>
            
            {/* Right column */}
            <div className="space-y-6">
              {/* Conversation Summary */}
              {connection.summary && (
                <div>
                  <h2 className="text-xl font-semibold border-b pb-2 mb-3">Conversation Summary</h2>
                  <p className="whitespace-pre-line">{connection.summary}</p>
                </div>
              )}
              
              {/* Fun Facts */}
              {connection.funFacts && connection.funFacts.length > 0 && (
                <div>
                  <h2 className="text-xl font-semibold border-b pb-2 mb-3">Fun Facts</h2>
                  <ul className="list-disc pl-5 space-y-1">
                    {connection.funFacts.map((fact, index) => (
                      <li key={index}>{fact}</li>
                    ))}
                  </ul>
                </div>
              )}
              
              {/* Notes */}
              {connection.notes && (
                <div>
                  <h2 className="text-xl font-semibold border-b pb-2 mb-3">Additional Notes</h2>
                  <p className="whitespace-pre-line">{connection.notes}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
} 