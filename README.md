# IMET - Post-Event Memory Capture

This Next.js application helps you remember people you've met by:
- Recording voice descriptions
- Typing descriptions
- Uploading images
- Using OpenAI to generate structured summaries

## Getting Started

1. Clone the repository
2. Install dependencies:
   ```bash
   npm install
   ```
3. Create a `.env.local` file in the root of the project with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```
4. Run the development server:
   ```bash
   npm run dev
   ```
5. Open [http://localhost:3000/memory-capture](http://localhost:3000/memory-capture) in your browser

## Features

- **Voice Recording**: Record audio descriptions of people you've met
- **Text Input**: Type descriptions directly
- **Image Upload**: Add photos from your meeting or event
- **AI-Powered Summaries**: Generate structured summaries using OpenAI

## Deployment

This application is designed to work with Vercel's serverless functions. To deploy:

1. Push your code to a GitHub repository
2. Connect the repository to Vercel
3. Add your `OPENAI_API_KEY` as an environment variable in the Vercel project settings
4. Deploy!

## Technical Details

- Built with Next.js App Router
- Uses OpenAI for text generation (GPT-4) and audio transcription (Whisper)
- Serverless API endpoints for scalability
- Client-side audio recording with the Web Audio API
