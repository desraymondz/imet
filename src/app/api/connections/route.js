import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';
import { promises as fsPromises } from 'fs';

// Path to our data file
const dataFilePath = path.join(process.cwd(), 'data', 'connections.json');

// Ensure the data directory exists
const ensureDataDirectory = async () => {
  const dataDir = path.join(process.cwd(), 'data');
  try {
    await fsPromises.access(dataDir);
  } catch (error) {
    await fsPromises.mkdir(dataDir, { recursive: true });
  }
};

// Read connections from JSON file
const getConnections = async () => {
  await ensureDataDirectory();
  
  try {
    await fsPromises.access(dataFilePath);
    const data = await fsPromises.readFile(dataFilePath, 'utf8');
    return JSON.parse(data);
  } catch (error) {
    // Return empty connections array if file doesn't exist or is invalid
    const initialData = { connections: [] };
    await fsPromises.writeFile(dataFilePath, JSON.stringify(initialData, null, 2));
    return initialData;
  }
};

// Write connections to JSON file
const saveConnections = async (data) => {
  await ensureDataDirectory();
  await fsPromises.writeFile(dataFilePath, JSON.stringify(data, null, 2));
};

// GET - Retrieve all connections
export async function GET() {
  try {
    const data = await getConnections();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error retrieving connections:', error);
    return NextResponse.json(
      { error: 'Failed to retrieve connections' },
      { status: 500 }
    );
  }
}

// POST - Create a new connection
export async function POST(request) {
  try {
    const newConnection = await request.json();
    
    // Validate the connection data
    if (!newConnection || typeof newConnection !== 'object') {
      return NextResponse.json(
        { error: 'Invalid connection data' },
        { status: 400 }
      );
    }
    
    // Generate a unique ID for the connection
    newConnection.id = Date.now().toString();
    newConnection.createdAt = new Date().toISOString();
    
    // Add the connection to the data file
    const data = await getConnections();
    data.connections.push(newConnection);
    await saveConnections(data);
    
    return NextResponse.json({ 
      message: 'Connection created successfully',
      connection: newConnection
    }, { status: 201 });
  } catch (error) {
    console.error('Error creating connection:', error);
    return NextResponse.json(
      { error: 'Failed to create connection' },
      { status: 500 }
    );
  }
} 