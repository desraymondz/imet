"use client";

import { useState, useEffect } from 'react';
import Link from 'next/link';
import Image from 'next/image';

export default function ConnectionsPage() {
  const [connections, setConnections] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedTags, setSelectedTags] = useState([]);
  const [allTags, setAllTags] = useState([]);

  useEffect(() => {
    // Fetch connections from API or local storage
    const fetchConnections = async () => {
      try {
        const response = await fetch('/api/connections');
        if (response.ok) {
          const data = await response.json();
          setConnections(data.connections);
          
          // Extract all unique tags
          const tags = new Set();
          data.connections.forEach(connection => {
            connection.tags?.forEach(tag => tags.add(tag));
          });
          setAllTags(Array.from(tags));
        } else {
          console.error('Failed to fetch connections');
        }
      } catch (error) {
        console.error('Error fetching connections:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchConnections();
  }, []);

  // Filter connections based on search term and selected tags
  const filteredConnections = connections.filter(connection => {
    const matchesSearch = searchTerm === '' || 
      connection.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      connection.summary?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      connection.interests?.some(interest => interest.toLowerCase().includes(searchTerm.toLowerCase()));
    
    const matchesTags = selectedTags.length === 0 || 
      selectedTags.every(tag => connection.tags?.includes(tag));
    
    return matchesSearch && matchesTags;
  });

  const toggleTag = (tag) => {
    setSelectedTags(prev => 
      prev.includes(tag) 
        ? prev.filter(t => t !== tag) 
        : [...prev, tag]
    );
  };

  return (
    <div className="max-w-7xl mx-auto p-6">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">Your Connections</h1>
        <Link 
          href="/memory-capture" 
          className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg"
        >
          Add New Connection
        </Link>
      </div>

      {/* Search and filter */}
      <div className="mb-8 space-y-4">
        <div className="flex">
          <input
            type="text"
            placeholder="Search connections..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full p-3 border rounded-lg"
          />
        </div>

        {allTags.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {allTags.map(tag => (
              <button
                key={tag}
                onClick={() => toggleTag(tag)}
                className={`px-3 py-1 rounded-full text-sm ${
                  selectedTags.includes(tag)
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-200 hover:bg-gray-300'
                }`}
              >
                {tag}
              </button>
            ))}
          </div>
        )}
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
        </div>
      ) : filteredConnections.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredConnections.map((connection) => (
            <ConnectionCard key={connection.id} connection={connection} />
          ))}
        </div>
      ) : (
        <div className="text-center py-12">
          <p className="text-xl text-gray-500">No connections found.</p>
          <p className="mt-2">Add your first connection from the memory capture page.</p>
        </div>
      )}
    </div>
  );
}

function ConnectionCard({ connection }) {
  return (
    <div className="border rounded-lg overflow-hidden shadow-md hover:shadow-lg transition-shadow duration-300">
      <div className="relative">
        {connection.image ? (
          <Image
            src={connection.image}
            alt={connection.name || 'Connection'}
            width={400}
            height={200}
            className="w-full h-48 object-cover"
          />
        ) : (
          <div className="w-full h-48 bg-gradient-to-r from-blue-100 to-blue-200 flex items-center justify-center">
            <span className="text-5xl font-bold text-blue-500">
              {connection.name ? connection.name.charAt(0).toUpperCase() : '?'}
            </span>
          </div>
        )}
      </div>

      <div className="p-5 space-y-4">
        <h2 className="text-xl font-bold">{connection.name || 'Unnamed Connection'}</h2>
        
        {/* Where & when you met */}
        {(connection.meetingLocation || connection.meetingDate) && (
          <div>
            <h3 className="text-sm font-semibold text-gray-500">MET AT</h3>
            <p>
              {connection.meetingLocation && connection.meetingLocation}
              {connection.meetingLocation && connection.meetingDate && ' · '}
              {connection.meetingDate && connection.meetingDate}
            </p>
          </div>
        )}
        
        {/* Summary */}
        {connection.summary && (
          <div>
            <h3 className="text-sm font-semibold text-gray-500">SUMMARY</h3>
            <p className="line-clamp-3">{connection.summary}</p>
          </div>
        )}
        
        {/* Interests */}
        {connection.interests && connection.interests.length > 0 && (
          <div>
            <h3 className="text-sm font-semibold text-gray-500">INTERESTS & GOALS</h3>
            <p className="line-clamp-2">{connection.interests.join(', ')}</p>
          </div>
        )}
        
        {/* Tags */}
        {connection.tags && connection.tags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {connection.tags.map(tag => (
              <span 
                key={tag} 
                className="inline-block px-2 py-1 bg-gray-100 text-gray-800 text-xs rounded-full"
              >
                {tag}
              </span>
            ))}
          </div>
        )}
        
        <Link 
          href={`/connections/${connection.id}`}
          className="block text-center mt-4 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-gray-800 font-medium"
        >
          View Details
        </Link>
      </div>
    </div>
  );
} 