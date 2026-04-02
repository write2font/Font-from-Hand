package com.example.backend.controller;

import com.example.backend.entity.Autobiography;
import com.example.backend.repository.AutobiographyRepository;
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

@RestController
@RequestMapping("/api/v1/autobiography")
@CrossOrigin(origins = "http://localhost:3000")
public class AutobiographyController {

    private final ObjectMapper objectMapper = new ObjectMapper();
    private final String autoDir = Paths.get(System.getProperty("user.dir"), "..", "autobiography").normalize().toString();
    private final AutobiographyRepository autobiographyRepository;

    public AutobiographyController(AutobiographyRepository autobiographyRepository) {
        this.autobiographyRepository = autobiographyRepository;
    }

    private static final List<String> QUESTIONS = List.of(
        "Q2. 부모님은 어떤 분이셨으며, 형제들 사이에서 주로 어떤 역할이었나요?",
        "Q3. 어린 시절, 우리 집이나 동네에서 가장 좋아했던 장소와 그곳의 분위기를 묘사해 주세요.",
        "Q4. 유년 시절을 떠올리면 가장 먼저 생각나는 상징적인 사건이나 장면 하나는 무엇인가요?",
        "Q5. 어린 시절의 꿈은 무엇이었으며, 현재의 직업이나 전공을 선택하게 된 결정적인 계기는 무엇이었나요?",
        "Q6. 학창 시절 가장 열정적으로 몰두했던 공부나 활동은 무엇이었나요?",
        "Q7. 청년 시절, 사회적으로나 개인적으로 가장 뜨거웠던 기억(예: 첫 취업, 시대적 사건 등)은 무엇인가요?",
        "Q8. 인생의 방향을 바꿔놓을 만큼 큰 영향을 준 스승이나 친구, 혹은 동료가 있나요?",
        "Q9. 인생에서 가장 힘들었던 시기는 언제였으며, 무엇이 당신을 가장 괴롭혔나요?",
        "Q10. 그 시련을 어떻게 버텨내셨으며, 그 과정에서 무엇을 배우셨나요?",
        "Q11. 내 인생에서 \"이것만큼은 정말 잘했다\"고 자부하는 가장 큰 업적이나 결과물은 무엇인가요?",
        "Q12. 인생의 경로가 180도 바뀌었던 결정적인 선택의 순간과 그 이유를 들려주세요.",
        "Q13. 평생을 지탱해 온 자신만의 좌우명이나 꼭 지키고자 했던 원칙은 무엇인가요?",
        "Q14. 다시 태어난다면 꼭 해보고 싶은 일이나, 후배 세대에게 꼭 전하고 싶은 한마디는 무엇인가요?",
        "Q15. 훗날 사람들이 당신을 어떤 단어 혹은 어떤 사람으로 기억해주길 바라시나요?"
    );

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
            @RequestParam("transcriptions")          String transcriptionsJson,
            @RequestParam("followup_transcriptions") String followupJson,
            @RequestParam("keywords")                String keywordsJson,
            @RequestParam(value = "title", required = false, defaultValue = "") String title,
            @RequestParam(value = "images", required = false) List<MultipartFile> images
    ) {
        Path tempJson = null;
        Path imgTemp = null;
        try {
            String userId = UUID.randomUUID().toString().substring(0, 8);

            String coverImagePath = null;
            if (images != null && !images.isEmpty()) {
                imgTemp = Files.createTempFile("auto_cover_", ".jpg");
                images.get(0).transferTo(imgTemp.toFile());
                coverImagePath = imgTemp.toString();
            }

            Map<String, Object> payload = new LinkedHashMap<>();
            payload.put("name", name);
            payload.put("birth", birth);
            payload.put("hometown", hometown);
            payload.put("user_id", userId);
            payload.put("questions", QUESTIONS);
            payload.put("transcriptions", objectMapper.readValue(transcriptionsJson, List.class));
            payload.put("followup_transcriptions", objectMapper.readValue(followupJson, List.class));
            payload.put("keywords", objectMapper.readValue(keywordsJson, List.class));
            payload.put("title", title);
            if (coverImagePath != null) payload.put("cover_image_path", coverImagePath);

            tempJson = Files.createTempFile("auto_generate_", ".json");
            Files.writeString(tempJson, objectMapper.writeValueAsString(payload), StandardCharsets.UTF_8);

            String scriptPath = Paths.get(autoDir, "generate_cli.py").toString();
            String output = runPython(scriptPath, tempJson.toString());

            Map<String, Object> result = objectMapper.readValue(output, Map.class);
            if (result.containsKey("error")) {
                return ResponseEntity.internalServerError().body(result);
            }

            String pdfPath = (String) result.get("pdf_path");

            // DB 저장 (user는 JWT 연동 후 팀원이 채워줄 것)
            autobiographyRepository.save(new Autobiography(null, name, title, pdfPath));

            // 다운로드 엔드포인트용 경로 갱신
            Files.createDirectories(Paths.get(autoDir, "output"));
            Files.writeString(Paths.get(autoDir, "output", "latest_pdf.txt"),
                pdfPath, StandardCharsets.UTF_8);

            return ResponseEntity.ok(Map.of("status", "success", "pdf_path", pdfPath));

        } catch (Exception e) {
            return ResponseEntity.internalServerError()
                    .body(Map.of("error", e.getMessage()));
        } finally {
            try { if (tempJson != null) Files.deleteIfExists(tempJson); } catch (IOException ignored) {}
            try { if (imgTemp  != null) Files.deleteIfExists(imgTemp);  } catch (IOException ignored) {}
        }
    }

    // ── 4. PDF 다운로드 ───────────────────────────────────────────────────────────
    @GetMapping("/download")
    public ResponseEntity<Resource> download() {
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

            Resource resource = new UrlResource(pdfFile.toURI());
            return ResponseEntity.ok()
                    .contentType(MediaType.APPLICATION_PDF)
                    .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"autobiography.pdf\"")
                    .body(resource);

        } catch (Exception e) {
            return ResponseEntity.internalServerError().build();
        }
    }

    // ── 공통: Python 실행 헬퍼 ────────────────────────────────────────────────────
    private String runPython(String... args) throws Exception {
        List<String> cmd = new ArrayList<>();
        cmd.add(Paths.get(autoDir, "venv", "bin", "python3").toString());
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
