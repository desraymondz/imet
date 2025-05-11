"use client";

import { useState, useRef } from 'react';
import Image from 'next/image';
import { useRouter } from 'next/navigation';

export default function MemoryCapturePage() {
  const router = useRouter();
  const [isRecording, setIsRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState(null);
  const [audioUrl, setAudioUrl] = useState('');
  const [images, setImages] = useState([]);
  const [description, setDescription] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [summary, setSummary] = useState('');
  const [connectionData, setConnectionData] = useState(null);
  
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];
      
      mediaRecorder.addEventListener('dataavailable', event => {
        audioChunksRef.current.push(event.data);
      });
      
      mediaRecorder.addEventListener('stop', () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        setAudioBlob(audioBlob);
        const audioUrl = URL.createObjectURL(audioBlob);
        setAudioUrl(audioUrl);
      });
      
      mediaRecorder.start();
      setIsRecording(true);
    } catch (error) {
      console.error('Error accessing microphone:', error);
      alert('Unable to access microphone. Please check permissions.');
    }
  };
  
  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      // Close the stream tracks
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
    }
  };
  
  const handleImageUpload = (event) => {
    const files = Array.from(event.target.files);
    const newImages = files.map(file => ({
      file,
      url: URL.createObjectURL(file)
    }));
    setImages([...images, ...newImages]);
  };
  
  const removeImage = (index) => {
    const newImages = [...images];
    URL.revokeObjectURL(newImages[index].url);
    newImages.splice(index, 1);
    setImages(newImages);
  };
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsProcessing(true);
    setSummary('');
    setConnectionData(null);
    
    try {
      // Determine if we should use FormData (for audio/images) or JSON
      const hasMediaContent = audioBlob || images.length > 0;
      
      let response;
      if (hasMediaContent) {
        // Use FormData for multimedia content
        const formData = new FormData();
        formData.append('description', description);
        
        if (audioBlob) {
          // Convert to mp3 or wav for better compatibility with OpenAI Whisper
          const audioFile = new File([audioBlob], 'recording.webm', { type: 'audio/webm' });
          formData.append('audio', audioFile);
        }
        
        images.forEach((image, index) => {
          formData.append(`image-${index}`, image.file);
        });
        
        response = await fetch('/api/generate-summary', {
          method: 'POST',
          body: formData,
        });
      } else {
        // Use JSON for text-only content
        response = await fetch('/api/generate-summary', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ text: description }),
        });
      }
      
      if (!response.ok) {
        throw new Error('Failed to generate summary');
      }
      
      const data = await response.json();
      setSummary(data.summary);
      
      // Extract structured data from summary for connection
      try {
        const parsedData = parseStructuredSummary(data.summary);
        setConnectionData(parsedData);
      } catch (parseError) {
        console.error('Error parsing summary:', parseError);
        // If parsing fails, create a basic connection object
        setConnectionData({
          name: extractNameFromSummary(data.summary) || 'Unnamed Connection',
          summary: data.summary,
          rawInput: description,
        });
      }
    } catch (error) {
      console.error('Error submitting form:', error);
      alert('An error occurred. Please try again.');
    } finally {
      setIsProcessing(false);
    }
  };
  
  const saveConnection = async () => {
    if (!connectionData) return;
    
    setIsProcessing(true);
    try {
      // Prepare connection data
      const connectionToSave = {
        ...connectionData,
        // If we have images, we need to handle image storage separately
        // For now, we're not handling image storage in this example
      };
      
      const response = await fetch('/api/connections', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(connectionToSave),
      });
      
      if (!response.ok) {
        throw new Error('Failed to save connection');
      }
      
      const result = await response.json();
      // Navigate to the connection page
      router.push(`/connections/${result.connection.id}`);
    } catch (error) {
      console.error('Error saving connection:', error);
      alert('Failed to save the connection. Please try again.');
    } finally {
      setIsProcessing(false);
    }
  };
  
  // Helper function to extract structured data from the summary
  const parseStructuredSummary = (summary) => {
    // This is a basic implementation - in a real app, you might use a more robust approach
    const sections = {};
    
    // Try to extract name
    const nameMatch = summary.match(/Name:([^\n]+)/i);
    const name = nameMatch ? nameMatch[1].trim() : null;
    
    // Try to extract meeting location
    const locationMatch = summary.match(/Location:([^\n]+)/i) || summary.match(/Met at:([^\n]+)/i);
    const meetingLocation = locationMatch ? locationMatch[1].trim() : null;
    
    // Try to extract meeting date
    const dateMatch = summary.match(/Date:([^\n]+)/i) || summary.match(/When:([^\n]+)/i);
    const meetingDate = dateMatch ? dateMatch[1].trim() : null;
    
    // Try to extract interests
    const interestsSection = summary.match(/Interests:([\s\S]*?)(?=\n\s*\n|\n\s*[A-Z]|$)/i);
    const interests = interestsSection 
      ? interestsSection[1].split(/[,•]/).map(item => item.trim()).filter(Boolean)
      : [];
    
    // Try to extract tags
    const tags = [];
    // Look for keywords in the summary to create tags
    const possibleTags = ['tech', 'business', 'design', 'marketing', 'finance', 'education', 'healthcare', 'sports'];
    possibleTags.forEach(tag => {
      if (summary.toLowerCase().includes(tag)) {
        tags.push(`#${tag}`);
      }
    });
    
    return {
      name,
      meetingLocation,
      meetingDate,
      summary,
      interests,
      tags,
      rawInput: description,
    };
  };
  
  // Helper function to extract just the name from the summary
  const extractNameFromSummary = (summary) => {
    const nameMatch = summary.match(/Name:([^\n]+)/i);
    return nameMatch ? nameMatch[1].trim() : null;
  };
  
  return (
    <div className="max-w-4xl mx-auto p-6 space-y-8">
      <h1 className="text-3xl font-bold">Post-Event Memory Capture</h1>
      <p className="text-lg">Record your thoughts about people you met or upload pictures and describe them.</p>
      
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Voice Recording Section */}
        <div className="p-4 border rounded-lg">
          <h2 className="text-xl font-semibold mb-4">Voice Recording</h2>
          <div className="flex items-center space-x-4">
            <button
              type="button"
              onClick={isRecording ? stopRecording : startRecording}
              className={`px-4 py-2 rounded-full ${isRecording ? 'bg-red-500 hover:bg-red-600' : 'bg-blue-500 hover:bg-blue-600'} text-white`}
            >
              {isRecording ? 'Stop Recording' : 'Start Recording'}
            </button>
            {audioUrl && (
              <audio controls src={audioUrl} className="w-full" />
            )}
          </div>
        </div>
        
        {/* Text Description */}
        <div className="p-4 border rounded-lg">
          <h2 className="text-xl font-semibold mb-4">Text Description</h2>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe who you met and any details you'd like to remember..."
            className="w-full p-3 border rounded-lg h-40"
            required={!audioBlob}
          />
        </div>
        
        {/* Image Upload */}
        <div className="p-4 border rounded-lg">
          <h2 className="text-xl font-semibold mb-4">Upload Images</h2>
          <input
            type="file"
            accept="image/*"
            multiple
            onChange={handleImageUpload}
            className="w-full p-2 border rounded-lg"
          />
          
          {images.length > 0 && (
            <div className="grid grid-cols-3 gap-4 mt-4">
              {images.map((image, index) => (
                <div key={index} className="relative">
                  <Image 
                    src={image.url} 
                    alt={`Uploaded image ${index + 1}`} 
                    width={150}
                    height={150}
                    className="object-cover rounded"
                  />
                  <button
                    type="button"
                    onClick={() => removeImage(index)}
                    className="absolute top-1 right-1 bg-red-500 text-white rounded-full w-6 h-6 flex items-center justify-center"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
        
        {/* Submit Button */}
        <button
          type="submit"
          disabled={isProcessing || (!description && !audioBlob)}
          className="w-full px-6 py-3 bg-green-500 hover:bg-green-600 text-white rounded-lg disabled:opacity-50"
        >
          {isProcessing ? 'Processing...' : 'Generate Summary'}
        </button>
      </form>
      
      {/* Results Section */}
      {summary && (
        <div className="p-6 border rounded-lg bg-gray-50 mt-8 space-y-6">
          <h2 className="text-xl font-semibold mb-4">Generated Summary</h2>
          <div className="whitespace-pre-line">{summary}</div>
          
          <div className="flex justify-end mt-4">
            <button
              onClick={saveConnection}
              disabled={isProcessing || !connectionData}
              className="px-6 py-3 bg-blue-500 hover:bg-blue-600 text-white rounded-lg disabled:opacity-50"
            >
              {isProcessing ? 'Saving...' : 'Save as Connection'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
} 