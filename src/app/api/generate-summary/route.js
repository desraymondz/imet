import { NextResponse } from 'next/server';
import OpenAI from 'openai';

// Initialize OpenAI client
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

export async function POST(request) {
  try {
    // Check if the request is multipart/form-data or JSON
    const contentType = request.headers.get('content-type') || '';
    
    let text = '';
    let audioTranscript = '';
    let formData;
    
    if (contentType.includes('multipart/form-data')) {
      // Handle form data with possible audio file
      formData = await request.formData();
      text = formData.get('description') || '';
      
      const audioFile = formData.get('audio');
      if (audioFile && audioFile instanceof Blob) {
        // Transcribe audio using OpenAI's API
        const transcription = await openai.audio.transcriptions.create({
          file: audioFile,
          model: 'whisper-1',
        });
        
        audioTranscript = transcription.text;
      }
      
      // Process images if needed (for future enhancement)
      // const images = [];
      // for (const [key, value] of formData.entries()) {
      //   if (key.startsWith('image-') && value instanceof Blob) {
      //     images.push(value);
      //   }
      // }
    } else {
      // Handle JSON request
      const jsonData = await request.json();
      text = jsonData.text || '';
      audioTranscript = jsonData.audioTranscript || '';
    }
    
    // Use either the text description or the transcribed audio
    const inputText = audioTranscript || text;
    
    if (!inputText || inputText.trim() === '') {
      return NextResponse.json(
        { error: 'No input text provided' },
        { status: 400 }
      );
    }

    // Create a prompt for OpenAI that will generate a more structured output
    const prompt = `
      Based on the following description about a person someone met, please generate a structured summary 
      with clear section headings and organized information. Be sure to include:
      
      1. Name: [Full name if mentioned, otherwise leave as "Unknown"]
      2. Physical Description: [Any details about appearance]
      3. Meeting Context: [Where and when they met]
      4. Personality Traits: [Notable characteristics of the person]
      5. Conversation Summary: [Brief overview of what was discussed]
      6. Interests & Goals: [List their interests, career goals, hobbies as bullet points]
      7. Key Talking Points: [Main topics discussed]
      8. Follow-up Items: [Any planned next steps or follow-ups]
      
      Input description: "${inputText}"
      
      Format the summary with clear headings for each section. Only include information that is directly 
      stated or strongly implied in the description. If information for a section is not available, please
      indicate this with "Not provided" rather than making assumptions.
    `;

    // Call OpenAI API
    const completion = await openai.chat.completions.create({
      model: "gpt-4-turbo",  // Choose an appropriate model
      messages: [
        {
          role: "system",
          content: "You are an assistant that helps users organize and structure information about people they've met. Your summaries are clear, well-formatted, and extract all relevant details while maintaining a professional tone."
        },
        {
          role: "user",
          content: prompt
        }
      ],
      temperature: 0.7,
      max_tokens: 800,
    });

    // Extract the generated summary
    const summary = completion.choices[0].message.content;

    return NextResponse.json({ summary });
  } catch (error) {
    console.error('Error generating summary:', error);
    return NextResponse.json(
      { error: 'Failed to generate summary' },
      { status: 500 }
    );
  }
} 