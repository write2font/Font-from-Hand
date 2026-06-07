package com.example.backend.controller;

import com.example.backend.entity.Autobiography;
import com.example.backend.entity.SurveyResponse;
import com.example.backend.repository.AutobiographyRepository;
import com.example.backend.repository.SurveyResponseRepository;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.core.io.Resource;
import org.springframework.core.io.UrlResource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/v1/autobiography")
public class AutobiographyController {

    private final ObjectMapper objectMapper = new ObjectMapper();
    private final String autoDir = Paths.get(System.getProperty("user.dir"), "..", "autobiography").normalize().toString();
    private final AutobiographyRepository autobiographyRepository;
    private final com.example.backend.repository.FontRepository fontRepository;
    private final SurveyResponseRepository surveyResponseRepository;

    public AutobiographyController(AutobiographyRepository autobiographyRepository,
                                   com.example.backend.repository.FontRepository fontRepository,
                                   SurveyResponseRepository surveyResponseRepository) {
        this.autobiographyRepository  = autobiographyRepository;
        this.fontRepository           = fontRepository;
        this.surveyResponseRepository = surveyResponseRepository;
    }

    // ── 1. STT: 음성 파일 → 텍스트 변환 ─────────────────────────────────────────
    @PostMapping("/transcribe")
    public ResponseEntity<Map<String, String>> transcribe(
            @RequestParam("audio") MultipartFile audioFile
    ) {
        String suffix = getExtension(audioFile.getOriginalFilename());
        Path tempAudio = null;
        try {
            tempAudio = Files.createTempFile("auto_audio_", suffix);
            audioFile.transferTo(tempAudio.toFile());

            String userId = "api_" + UUID.randomUUID().toString().substring(0, 8);
            String scriptPath = Paths.get(autoDir, "stt_cli.py").toString();

            String output = runPython(scriptPath, tempAudio.toString(), userId);

            Map<String, Object> result = objectMapper.readValue(output, Map.class);
            if (result.containsKey("error")) {
                return ResponseEntity.internalServerError()
                        .body(Map.of("error", (String) result.get("error")));
            }

            return ResponseEntity.ok(Map.of("text", (String) result.getOrDefault("text", "")));

        } catch (Exception e) {
            return ResponseEntity.internalServerError()
                    .body(Map.of("error", e.getMessage()));
        } finally {
            try { if (tempAudio != null) Files.deleteIfExists(tempAudio); } catch (IOException ignored) {}
        }
    }

    // ── 2. 키워드/제목 추천 ──────────────────────────────────────────────────────
    @PostMapping("/suggest")
    public ResponseEntity<Map<String, Object>> suggest(
            @RequestBody Map<String, Object> body
    ) {
        Path tempJson = null;
        try {
            tempJson = Files.createTempFile("auto_suggest_", ".json");
            Files.writeString(tempJson, objectMapper.writeValueAsString(body), StandardCharsets.UTF_8);

            String scriptPath = Paths.get(autoDir, "suggest_cli.py").toString();
            String output = runPython(scriptPath, tempJson.toString());

            Map<String, Object> result = objectMapper.readValue(output, Map.class);
            if (result.containsKey("error")) {
                return ResponseEntity.internalServerError().body(result);
            }

            return ResponseEntity.ok(result);

        } catch (Exception e) {
            return ResponseEntity.internalServerError()
                    .body(Map.of("error", e.getMessage()));
        } finally {
            try { if (tempJson != null) Files.deleteIfExists(tempJson); } catch (IOException ignored) {}
        }
    }

    // ── 3. AI 추가질문 생성 ──────────────────────────────────────────────────────
    @PostMapping("/generate-followups")
    public ResponseEntity<Map<String, Object>> generateFollowups(
            @RequestBody Map<String, Object> body
    ) {
        Path tempJson = null;
        try {
            tempJson = Files.createTempFile("auto_followup_", ".json");
            Files.writeString(tempJson, objectMapper.writeValueAsString(body), StandardCharsets.UTF_8);

            String scriptPath = Paths.get(autoDir, "followup_cli.py").toString();
            String output = runPython(scriptPath, tempJson.toString());

            Map<String, Object> result = objectMapper.readValue(output, Map.class);
            if (result.containsKey("error")) {
                return ResponseEntity.internalServerError().body(result);
            }

            return ResponseEntity.ok(result);

        } catch (Exception e) {
            return ResponseEntity.internalServerError()
                    .body(Map.of("error", e.getMessage()));
        } finally {
            try { if (tempJson != null) Files.deleteIfExists(tempJson); } catch (IOException ignored) {}
        }
    }

    // ── 3. 자서전 PDF 생성 ────────────────────────────────────────────────────────
    @PostMapping("/generate")
    public ResponseEntity<Map<String, Object>> generate(
            @RequestParam("name")                    String name,
            @RequestParam("birth")                   String birth,
            @RequestParam("hometown")                String hometown,
            @RequestParam("questions")               String questionsJson,
            @RequestParam("transcriptions")          String transcriptionsJson,
            @RequestParam("followup_transcriptions") String followupJson,
            @RequestParam(value = "free_text",      required = false, defaultValue = "") String freeText,
            @RequestParam("keywords")                String keywordsJson,
            @RequestParam(value = "title",          required = false, defaultValue = "") String title,
            @RequestParam(value = "font_id",        required = false, defaultValue = "") String fontId,
            @RequestParam(value = "font_file",      required = false) MultipartFile fontFile,
            @RequestParam(value = "images",         required = false) List<MultipartFile> images,
            @RequestParam(value = "image_tags",     required = false, defaultValue = "[]") String imageTagsJson,
            @RequestParam(value = "writing_style",   required = false, defaultValue = "서술체") String writingStyle,
            @RequestParam(value = "gender",          required = false, defaultValue = "") String gender,
            @RequestParam(value = "military_service",required = false, defaultValue = "") String militaryService,
            @RequestParam(value = "education",       required = false, defaultValue = "") String education,
            @RequestParam(value = "religion",        required = false, defaultValue = "") String religion
    ) {
        Path tempJson = null;
        Path tempFontPath = null;
        List<Path> tempImagePaths = new java.util.ArrayList<>();
        try {
            String userId = UUID.randomUUID().toString().substring(0, 8);

            // 업로드 이미지: 경로 + 상황 태그를 묶어서 Python에 전달
            List<String> imageTags = objectMapper.readValue(imageTagsJson, List.class);
            List<Map<String, String>> extraImages = new java.util.ArrayList<>();
            if (images != null && !images.isEmpty()) {
                for (int i = 0; i < images.size(); i++) {
                    Path extraTemp = Files.createTempFile("auto_img_" + i + "_", ".jpg");
                    images.get(i).transferTo(extraTemp.toFile());
                    tempImagePaths.add(extraTemp);
                    Map<String, String> imgInfo = new LinkedHashMap<>();
                    imgInfo.put("path", extraTemp.toString());
                    imgInfo.put("tag", i < imageTags.size() ? imageTags.get(i) : "");
                    extraImages.add(imgInfo);
                }
            }

            Map<String, Object> payload = new LinkedHashMap<>();
            payload.put("name", name);
            payload.put("birth", birth);
            payload.put("hometown", hometown);
            payload.put("user_id", userId);
            payload.put("writing_style", writingStyle);
            payload.put("gender", gender);
            payload.put("military_service", militaryService);
            payload.put("education", education);
            payload.put("religion", religion);
            payload.put("questions", objectMapper.readValue(questionsJson, List.class));
            payload.put("transcriptions", objectMapper.readValue(transcriptionsJson, List.class));
            payload.put("followup_transcriptions", objectMapper.readValue(followupJson, List.class));
            payload.put("free_text", freeText);
            payload.put("keywords", objectMapper.readValue(keywordsJson, List.class));
            payload.put("title", title);
            if (!extraImages.isEmpty()) payload.put("extra_images", extraImages);
            // 업로드 폰트 파일 우선, 없으면 font_id로 조회
            if (fontFile != null && !fontFile.isEmpty()) {
                String origName = fontFile.getOriginalFilename();
                String ext = (origName != null && origName.contains("."))
                    ? origName.substring(origName.lastIndexOf('.')) : ".ttf";
                tempFontPath = Files.createTempFile("auto_font_", ext);
                fontFile.transferTo(tempFontPath.toFile());
                payload.put("font_path", tempFontPath.toString());
            } else if (!fontId.isEmpty()) {
                fontRepository.findByFontId(fontId)
                    .ifPresent(f -> payload.put("font_path", f.getTtfPath()));
            }

            tempJson = Files.createTempFile("auto_generate_", ".json");
            Files.writeString(tempJson, objectMapper.writeValueAsString(payload), StandardCharsets.UTF_8);

            String scriptPath = Paths.get(autoDir, "generate_cli.py").toString();
            String output = runPython(scriptPath, tempJson.toString());

            Map<String, Object> result = objectMapper.readValue(output, Map.class);
            if (result.containsKey("error")) {
                return ResponseEntity.internalServerError().body(result);
            }

            String pdfPath = (String) result.get("pdf_path");

            Autobiography saved = autobiographyRepository.save(new Autobiography(null, name, title, pdfPath));

            // 다운로드 엔드포인트용 경로 갱신
            Files.createDirectories(Paths.get(autoDir, "output"));
            Files.writeString(Paths.get(autoDir, "output", "latest_pdf.txt"),
                pdfPath, StandardCharsets.UTF_8);

            return ResponseEntity.ok(Map.of("status", "success", "pdf_path", pdfPath, "id", saved.getId()));

        } catch (Exception e) {
            return ResponseEntity.internalServerError()
                    .body(Map.of("error", e.getMessage()));
        } finally {
            try { if (tempJson     != null) Files.deleteIfExists(tempJson);     } catch (IOException ignored) {}
            try { if (tempFontPath != null) Files.deleteIfExists(tempFontPath); } catch (IOException ignored) {}
            for (Path p : tempImagePaths) {
                try { Files.deleteIfExists(p); } catch (IOException ignored) {}
            }
        }
    }

    // ── 4. 자서전 목록 조회 ────────────────────────────────────────────────────────
    @GetMapping("/list")
    public ResponseEntity<List<Map<String, Object>>> list() {
        List<Autobiography> all = autobiographyRepository.findAll();
        all.sort((a, b) -> b.getCreatedAt().compareTo(a.getCreatedAt()));
        List<Map<String, Object>> result = all.stream().map(a -> {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("id", a.getId());
            m.put("subjectName", a.getSubjectName());
            m.put("title", a.getTitle());
            m.put("createdAt", a.getCreatedAt());
            return m;
        }).collect(Collectors.toList());
        return ResponseEntity.ok(result);
    }

    // ── 5. 자서전 삭제 ────────────────────────────────────────────────────────────
    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable long id) {
        if (!autobiographyRepository.existsById(id)) return ResponseEntity.notFound().build();
        autobiographyRepository.deleteById(id);
        return ResponseEntity.noContent().build();
    }

    // ── 6. 설문 저장 ──────────────────────────────────────────────────────────────
    @PostMapping("/{id}/survey")
    public ResponseEntity<Void> saveSurvey(
            @PathVariable long id,
            @RequestBody Map<String, Object> body
    ) {
        Autobiography autobiography = autobiographyRepository.findById(id).orElse(null);
        if (autobiography == null) return ResponseEntity.notFound().build();
        try {
            String ratings  = objectMapper.writeValueAsString(body.get("ratings"));
            String freeText = (String) body.getOrDefault("freeText", "");
            surveyResponseRepository.save(new SurveyResponse(autobiography, ratings, freeText));
            return ResponseEntity.ok().build();
        } catch (Exception e) {
            return ResponseEntity.internalServerError().build();
        }
    }

    // ── 7. 설문 결과 전체 조회 (연구/검토용) ───────────────────────────────────────
    @GetMapping("/surveys")
    public ResponseEntity<List<Map<String, Object>>> listSurveys() {
        List<Map<String, Object>> result = surveyResponseRepository.findAll().stream().map(s -> {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("id",             s.getId());
            m.put("autobiographyId", s.getAutobiography().getId());
            m.put("subjectName",    s.getAutobiography().getSubjectName());
            m.put("ratings",        s.getRatings());
            m.put("freeText",       s.getFreeText());
            m.put("createdAt",      s.getCreatedAt());
            return m;
        }).collect(Collectors.toList());
        return ResponseEntity.ok(result);
    }

    // ── 8. 개별 PDF 다운로드 ───────────────────────────────────────────────────────
    @GetMapping("/download/{id}")
    public ResponseEntity<Resource> downloadById(
            @PathVariable long id,
            @RequestParam(value = "inline", defaultValue = "false") boolean inline
    ) {
        Autobiography autobiography = autobiographyRepository.findById(id).orElse(null);
        if (autobiography == null) return ResponseEntity.notFound().build();
        try {
            File pdfFile = new File(autobiography.getPdfPath());
            if (!pdfFile.exists()) return ResponseEntity.notFound().build();
            Resource resource = new UrlResource(pdfFile.toURI());
            String disposition = inline ? "inline" : "attachment; filename=\"autobiography.pdf\"";
            return ResponseEntity.ok()
                    .contentType(MediaType.APPLICATION_PDF)
                    .header(HttpHeaders.CONTENT_DISPOSITION, disposition)
                    .body(resource);
        } catch (Exception e) {
            return ResponseEntity.internalServerError().build();
        }
    }

    // ── 6. PDF 다운로드 / 미리보기 ──────────────────────────────────────────────────
    @GetMapping("/download")
    public ResponseEntity<Resource> download(
            @RequestParam(value = "inline", defaultValue = "false") boolean inline
    ) {
        try {
            Path latestTxt = Paths.get(autoDir, "output", "latest_pdf.txt");
            if (!Files.exists(latestTxt)) {
                return ResponseEntity.notFound().build();
            }

            String pdfPath = Files.readString(latestTxt, StandardCharsets.UTF_8).trim();
            File pdfFile = new File(pdfPath);
            if (!pdfFile.exists()) {
                return ResponseEntity.notFound().build();
            }

            String disposition = inline ? "inline" : "attachment; filename=\"autobiography.pdf\"";
            Resource resource = new UrlResource(pdfFile.toURI());
            return ResponseEntity.ok()
                    .contentType(MediaType.APPLICATION_PDF)
                    .header(HttpHeaders.CONTENT_DISPOSITION, disposition)
                    .body(resource);

        } catch (Exception e) {
            return ResponseEntity.internalServerError().build();
        }
    }

    // ── 공통: Python 실행 헬퍼 ────────────────────────────────────────────────────
    private String runPython(String... args) throws Exception {
        List<String> cmd = new ArrayList<>();
        String pythonCmd = System.getProperty("os.name").toLowerCase().contains("win") ? "python" : "python3";
        cmd.add(pythonCmd);
        cmd.addAll(Arrays.asList(args));

        ProcessBuilder pb = new ProcessBuilder(cmd);
        pb.directory(new File(autoDir));

        Process process = pb.start();

        // stderr를 백그라운드 스레드로 소비 (stdout 읽기 전에 막히지 않도록)
        Thread errThread = new Thread(() -> {
            try (BufferedReader err = new BufferedReader(new InputStreamReader(process.getErrorStream()))) {
                String line;
                while ((line = err.readLine()) != null)
                    System.out.println("[Python] " + line);
            } catch (IOException ignored) {}
        });
        errThread.setDaemon(true);
        errThread.start();

        // stdout에서 마지막 JSON 행 추출
        String lastJson = "";
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) {
                String trimmed = line.trim();
                if (trimmed.startsWith("{") || trimmed.startsWith("["))
                    lastJson = trimmed;
                else
                    System.out.println("[Python] " + line);
            }
        }

        process.waitFor();
        return lastJson;
    }

    private String getExtension(String filename) {
        if (filename == null || !filename.contains(".")) return ".webm";
        return "." + filename.substring(filename.lastIndexOf('.') + 1);
    }
}
