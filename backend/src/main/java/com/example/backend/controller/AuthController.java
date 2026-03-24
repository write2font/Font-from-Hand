package com.example.backend.controller;

import com.example.backend.dto.SignInRequest;
import com.example.backend.dto.SignUpRequest;
import com.example.backend.service.AuthService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/auth")
@RequiredArgsConstructor
public class AuthController {

  private final AuthService authService;

  @PostMapping("/signup")
  public ResponseEntity<String> signUp(@RequestBody SignUpRequest request) {
    authService.signUp(request);
    return ResponseEntity.ok("회원가입이 성공적으로 완료되었습니다.");
  }

  @PostMapping("/signin")
  public ResponseEntity<String> signIn(@RequestBody SignInRequest request) {
    // JWT를 만든 후에 연결
    return ResponseEntity.ok("로그인 요청을 확인했습니다.");
  }
}
