package com.example.backend.controller;

import com.example.backend.service.FontService;
import lombok.RequiredArgsConstructor;
import org.springframework.core.io.Resource;
import org.springframework.core.io.UrlResource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.File;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/fonts")
@CrossOrigin(origins = "http://localhost:3000")
@RequiredArgsConstructor
public class FontController {

    private final FontService fontService;

    @PostMapping("/upload")
    public ResponseEntity<?> uploadImages(
        @RequestParam("files") List<MultipartFile> files,
        @CookieValue(name = "accessToken", required = false) String token
    ) {
        if (token == null) {
            return ResponseEntity.status(401).body("로그인이 필요합니다.");
        }
        if (files == null || files.isEmpty()) {
            return ResponseEntity.badRequest().body("업로드할 이미지가 없습니다.");
        }
        try {
            String fontId = fontService.uploadFont(files, token);
            return ResponseEntity.ok(Map.of("fontId", fontId, "message", "폰트 생성 완료"));
        } catch (RuntimeException e) {
            return ResponseEntity.status(401).body(e.getMessage());
        } catch (Exception e) {
            e.printStackTrace();
            return ResponseEntity.internalServerError().body("에러 발생: " + e.getMessage());
        }
    }

    @GetMapping("/download")
    public ResponseEntity<Resource> downloadFont(
        @CookieValue(name = "accessToken", required = false) String token
    ) {
        if (token == null) {
            return ResponseEntity.status(401).build();
        }
        try {
            File ttfFile = fontService.downloadFont(token);
            Resource resource = new UrlResource(ttfFile.toURI());
            return ResponseEntity.ok()
                .contentType(MediaType.APPLICATION_OCTET_STREAM)
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"MyHandwriting.ttf\"")
                .body(resource);
        } catch (RuntimeException e) {
            return ResponseEntity.status(404).build();
        } catch (Exception e) {
            e.printStackTrace();
            return ResponseEntity.internalServerError().build();
        }
    }
}