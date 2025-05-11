import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';
import { promises as fsPromises } from 'fs';

// Path to connections data file (we'll use this to generate relevant nudges)
const connectionsFilePath = path.join(process.cwd(), 'data', 'connections.json');

// Get connections data
const getConnections = async () => {
  try {
    await fsPromises.access(connectionsFilePath);
    const data = await fsPromises.readFile(connectionsFilePath, 'utf8');
    return JSON.parse(data);
  } catch (error) {
    return { connections: [] };
  }
};

// Generate intelligent nudges based on connections data
// This is a simplified version - in a real app, you would use more sophisticated algorithms
// and possibly integrate with calendar, cultural events API, etc.
const generateNudges = async () => {
  const { connections } = await getConnections();
  
  if (!connections || connections.length === 0) {
    return [];
  }
  
  const nudges = [];
  const currentDate = new Date();
  
  // For each connection, generate relevant nudges
  connections.forEach((connection, index) => {
    // Check if this is a recent connection (less than a month old)
    if (connection.createdAt) {
      const createdDate = new Date(connection.createdAt);
      const daysSinceCreated = Math.floor((currentDate - createdDate) / (1000 * 60 * 60 * 24));
      
      // Follow-up nudge for recent connections (2 weeks)
      if (daysSinceCreated >= 14 && daysSinceCreated <= 16) {
        nudges.push({
          id: `followup-${connection.id}`,
          connectionId: connection.id,
          connectionName: connection.name || 'your connection',
          type: 'followup',
          title: `It's been two weeks since you connected with ${connection.name || 'someone new'}`,
          description: 'Consider reaching out to strengthen the connection.',
          priority: 'medium',
          action: 'message',
          dueDate: new Date().toISOString()
        });
      }
    }
    
    // Special event nudges
    // Here we use current month to simulate seasonal events
    const currentMonth = currentDate.getMonth();
    
    // Sample seasonal events
    if (currentMonth === 11) { // December
      if (index % 3 === 0) { // Just use a simple algorithm to assign to some connections
        nudges.push({
          id: `holiday-${connection.id}`,
          connectionId: connection.id,
          connectionName: connection.name || 'your connection',
          type: 'event',
          title: `Holiday season is here — send ${connection.name || 'your connection'} your wishes!`,
          description: 'Holidays are a great time to reconnect.',
          priority: 'medium',
          action: 'message',
          dueDate: new Date(currentDate.getFullYear(), 11, 25).toISOString()
        });
      }
    } else if (currentMonth === 9) { // October
      if (index % 4 === 0) {
        nudges.push({
          id: `halloween-${connection.id}`,
          connectionId: connection.id,
          connectionName: connection.name || 'your connection',
          type: 'event',
          title: `Halloween is coming up — check in with ${connection.name || 'your connection'}`,
          description: 'Maybe they have plans you could join?',
          priority: 'low',
          action: 'message',
          dueDate: new Date(currentDate.getFullYear(), 9, 31).toISOString()
        });
      }
    }
    
    // Interest-based nudges
    if (connection.interests && connection.interests.length > 0) {
      const interests = connection.interests.map(i => i.toLowerCase());
      
      // Sports interest
      if (interests.some(i => i.includes('basketball') || i.includes('nba') || i.includes('lakers'))) {
        nudges.push({
          id: `basketball-${connection.id}`,
          connectionId: connection.id,
          connectionName: connection.name || 'your connection',
          type: 'interest',
          title: `You both love basketball — playoffs are happening now!`,
          description: `Want to check in with ${connection.name || 'your connection'} about the latest games?`,
          priority: 'low',
          action: 'message',
          dueDate: new Date(currentDate.getTime() + 2 * 24 * 60 * 60 * 1000).toISOString() // 2 days from now
        });
      }
      
      // Tech interest
      if (interests.some(i => i.includes('tech') || i.includes('programming') || i.includes('software'))) {
        nudges.push({
          id: `tech-${connection.id}`,
          connectionId: connection.id,
          connectionName: connection.name || 'your connection',
          type: 'interest',
          title: `Share that tech article with ${connection.name || 'your connection'}`,
          description: 'You both share an interest in technology.',
          priority: 'medium',
          action: 'email',
          dueDate: new Date(currentDate.getTime() + 1 * 24 * 60 * 60 * 1000).toISOString() // 1 day from now
        });
      }
    }
    
    // Add some sample special ones for the first few connections
    if (index === 0) {
      nudges.push({
        id: `diwali-${connection.id}`,
        connectionId: connection.id,
        connectionName: connection.name || 'Arjun',
        type: 'event',
        title: `Today's Diwali — wish ${connection.name || 'Arjun'} a good one.`,
        description: "You met them at that sustainability event.",
        priority: 'high',
        action: 'message',
        dueDate: new Date().toISOString()
      });
    } else if (index === 1) {
      nudges.push({
        id: `game-${connection.id}`,
        connectionId: connection.id,
        connectionName: connection.name || 'Chris',
        type: 'interest',
        title: `You both love the Lakers — game night tonight.`,
        description: `Want to text ${connection.name || 'Chris'}?`,
        priority: 'medium',
        action: 'message',
        dueDate: new Date().toISOString()
      });
    } else if (index === 2) {
      nudges.push({
        id: `internship-${connection.id}`,
        connectionId: connection.id,
        connectionName: connection.name || 'Alisha',
        type: 'followup',
        title: `You said you'd check in with ${connection.name || 'Alisha'} after their internship.`,
        description: "That was 2 months ago. Time to follow up?",
        priority: 'low',
        action: 'call',
        dueDate: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString()
      });
    }
  });
  
  // Sort nudges by priority and date
  return nudges.sort((a, b) => {
    const priorityScore = { high: 3, medium: 2, low: 1 };
    const aScore = priorityScore[a.priority] || 0;
    const bScore = priorityScore[b.priority] || 0;
    
    return bScore - aScore || new Date(a.dueDate) - new Date(b.dueDate);
  });
};

// GET - Retrieve all nudges
export async function GET() {
  try {
    const nudges = await generateNudges();
    
    return NextResponse.json({ nudges });
  } catch (error) {
    console.error('Error generating nudges:', error);
    return NextResponse.json(
      { error: 'Failed to generate nudges' },
      { status: 500 }
    );
  }
}

// DELETE - Dismiss a specific nudge
export async function DELETE(request) {
  // In a real app, you would store dismissed nudges in a database
  // For now, we'll just return a success response
  return NextResponse.json({ 
    message: 'Nudge dismissed successfully',
  });
} 