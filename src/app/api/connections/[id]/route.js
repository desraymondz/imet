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

// GET - Retrieve a specific connection
export async function GET(request, { params }) {
  try {
    const { id } = params;
    const data = await getConnections();
    
    const connection = data.connections.find(conn => conn.id === id);
    
    if (!connection) {
      return NextResponse.json(
        { error: 'Connection not found' },
        { status: 404 }
      );
    }
    
    return NextResponse.json({ connection });
  } catch (error) {
    console.error('Error retrieving connection:', error);
    return NextResponse.json(
      { error: 'Failed to retrieve connection' },
      { status: 500 }
    );
  }
}

// PUT - Update a specific connection
export async function PUT(request, { params }) {
  try {
    const { id } = params;
    const updatedConnection = await request.json();
    
    const data = await getConnections();
    const index = data.connections.findIndex(conn => conn.id === id);
    
    if (index === -1) {
      return NextResponse.json(
        { error: 'Connection not found' },
        { status: 404 }
      );
    }
    
    // Preserve the ID and createdAt fields
    updatedConnection.id = id;
    updatedConnection.createdAt = data.connections[index].createdAt;
    updatedConnection.updatedAt = new Date().toISOString();
    
    // Update the connection
    data.connections[index] = updatedConnection;
    await saveConnections(data);
    
    return NextResponse.json({ 
      message: 'Connection updated successfully',
      connection: updatedConnection
    });
  } catch (error) {
    console.error('Error updating connection:', error);
    return NextResponse.json(
      { error: 'Failed to update connection' },
      { status: 500 }
    );
  }
}

// DELETE - Remove a specific connection
export async function DELETE(request, { params }) {
  try {
    const { id } = params;
    const data = await getConnections();
    
    const index = data.connections.findIndex(conn => conn.id === id);
    
    if (index === -1) {
      return NextResponse.json(
        { error: 'Connection not found' },
        { status: 404 }
      );
    }
    
    // Remove the connection
    data.connections.splice(index, 1);
    await saveConnections(data);
    
    return NextResponse.json({ 
      message: 'Connection deleted successfully' 
    });
  } catch (error) {
    console.error('Error deleting connection:', error);
    return NextResponse.json(
      { error: 'Failed to delete connection' },
      { status: 500 }
    );
  }
} 