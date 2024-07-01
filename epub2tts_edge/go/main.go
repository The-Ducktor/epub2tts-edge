package main

import (
	"fmt"
	"log"
	"os"
	"os/exec"
	"strings"
	"sync"
)

// Define paths
const (
	filePath   = "/Users/jacks/Documents/Git/epub2tts-edge/epub2tts_edge/file.txt"
	outputDir  = "/Users/jacks/Documents/Git/epub2tts-edge/epub2tts_edge/output/"
	edgeTTSBin = "edge-tts" // Update with your edge-tts binary path
)

func main() {
	// Create output directory if it doesn't exist
	if err := os.MkdirAll(outputDir, 0755); err != nil {
		log.Fatalf("Error creating output directory: %v", err)
	}

	// Read text file content
	content, err := os.ReadFile(filePath)
	if err != nil {
		log.Fatalf("Error reading file: %v", err)
	}

	// Split content into chapters
	chapters := strings.Split(string(content), "# ")
	fmt.Printf("Number of chapters found: %d\n", len(chapters))

	var wg sync.WaitGroup
	wg.Add(len(chapters))

	for chapterNumber, chapter := range chapters {
		go processChapter(chapterNumber+1, chapter, &wg)
	}

	wg.Wait()
	fmt.Println("All chapters processed successfully.")
}

func processChapter(chapterNumber int, chapterContent string, wg *sync.WaitGroup) {
	defer wg.Done()

	// Split chapter into sentences
	sentences := strings.Split(chapterContent, "\n")
	fmt.Printf("Processing Chapter %d with %d sentences...\n", chapterNumber, len(sentences))

	var wgSentences sync.WaitGroup
	wgSentences.Add(len(sentences))

	for sentenceIndex, sentence := range sentences {
		go func(index int, sentence string) {
			defer wgSentences.Done()
			tempFileName := fmt.Sprintf("%s/pg%d.flac", outputDir, index+1)
			if _, err := os.Stat(tempFileName); err == nil {
				return // File already exists, skip processing
			}

			if err := runTTS(sentence, tempFileName); err != nil {
				fmt.Printf("Error processing sentence %d: %v\n", index+1, err)
			}
		}(sentenceIndex, sentence)
	}

	wgSentences.Wait()

	// Combine audio files into a single chapter file
	var files []string
	for i := 1; i <= len(sentences); i++ {
		files = append(files, fmt.Sprintf("%s/pg%d.flac", outputDir, i))
	}

	combinedFileName := fmt.Sprintf("%s/chapter_%d.wav", outputDir, chapterNumber)
	if err := combineAudio(files, combinedFileName); err != nil {
		fmt.Printf("Error combining audio for Chapter %d: %v\n", chapterNumber, err)
	}

	// Clean up temporary files
	for _, file := range files {
		if err := os.Remove(file); err != nil {
			fmt.Printf("Error removing file %s: %v\n", file, err)
		}
	}

	fmt.Printf("Chapter %d processed successfully.\n", chapterNumber)
}

func runTTS(sentence, fileName string) error {
	cmdArgs := []string{"-t", sentence, "-f", fileName, "-v", "en-US-BrianNeural"}
	cmd := exec.Command(edgeTTSBin, cmdArgs...)
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("error running edge-tts: %v", err)
	}
	return nil
}

func combineAudio(inputFiles []string, outputFile string) error {
	args := []string{"-y", "-i", "concat:" + strings.Join(inputFiles, "|"), "-c", "copy", outputFile}
	cmd := exec.Command("ffmpeg", args...)
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("error running ffmpeg: %v", err)
	}
	return nil
}
