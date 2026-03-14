package com.example.backend.controller;

import org.springframework.core.io.Resource;
import org.springframework.core.io.UrlResource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.BufferedReader;
import java.io.File;
import java.io.InputStreamReader;
import java.nio.file.Paths;
import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/fonts")
@CrossOrigin(origins = "http://localhost:3000")
public class FontController {

  @PostMapping("/upload")
  public String uploadImages(@RequestParam("files") List<MultipartFile> files) {
    if (files == null || files.isEmpty()) {
      return "실패: 업로드할 이미지가 없습니다.";
    }

    try {
      String jobId = UUID.randomUUID().toString();
      String baseDir = System.getProperty("user.dir"); // FFH/backend 폴더
      String uploadPath = Paths.get(baseDir, "uploads", jobId).toString();

      saveFiles(files, uploadPath);

      String pythonScriptPath = Paths.get(baseDir, "..", "font-engine", "main.py").normalize().toString();
      String outputTtfPath = Paths.get(uploadPath, "MyHandwriting.ttf").toString();

      boolean isSuccess = runPythonEngine(pythonScriptPath, uploadPath, outputTtfPath);

      if (isSuccess) {
        return "성공: 폰트 생성 완료! (ID: " + jobId + ")";
      } else {
        return "실패: 파이썬 폰트 생성 중 에러 발생";
      }

    } catch (Exception e) {
      e.printStackTrace();
      return "에러 발생: " + e.getMessage();
    }
  }

  @GetMapping("/download")
  public ResponseEntity<Resource> downloadFont() {
    try {
      String baseDir = System.getProperty("user.dir");
      File uploadsDir = new File(baseDir, "uploads");

      File[] jobDirs = uploadsDir.listFiles(File::isDirectory);
      if (jobDirs == null || jobDirs.length == 0) {
        return ResponseEntity.notFound().build();
      }

      File latestDir = jobDirs[0];
      for (File dir : jobDirs) {
        if (dir.lastModified() > latestDir.lastModified()) {
          latestDir = dir;
        }
      }

      File ttfFile = new File(latestDir, "MyHandwriting.ttf");
      if (!ttfFile.exists()) {
        return ResponseEntity.notFound().build();
      }

      Resource resource = new UrlResource(ttfFile.toURI());

      return ResponseEntity.ok()
        .contentType(MediaType.APPLICATION_OCTET_STREAM)
        .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"MyHandwriting.ttf\"")
        .body(resource);

    } catch (Exception e) {
      e.printStackTrace();
      return ResponseEntity.internalServerError().build();
    }
  }

  private void saveFiles(List<MultipartFile> files, String uploadPath) throws Exception {
    File directory = new File(uploadPath);
    if (!directory.exists()) directory.mkdirs();

    for (MultipartFile file : files) {
      String originalName = file.getOriginalFilename();
      if (originalName == null) continue;

      String fileNameOnly = originalName.replaceAll("[^0-9]", "");
      String saveName;
      if (!fileNameOnly.isEmpty()) {
        int fileNumber = Integer.parseInt(fileNameOnly);
        saveName = String.format("%02d.jpg", fileNumber);
      } else {
        saveName = originalName;
      }

      file.transferTo(new File(uploadPath + File.separator + saveName));
    }
  }
  
  private boolean runPythonEngine(String scriptPath, String inputDir, String outputTtfPath) {
    try {
      ProcessBuilder pb = new ProcessBuilder("python3", "-u", scriptPath, inputDir, outputTtfPath);
      pb.redirectErrorStream(true);
      Process process = pb.start();

      BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()));
      String line;
      while ((line = reader.readLine()) != null) {
        System.out.println("[Python Log] " + line);
      }

      int exitCode = process.waitFor();
      return exitCode == 0;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }
}
