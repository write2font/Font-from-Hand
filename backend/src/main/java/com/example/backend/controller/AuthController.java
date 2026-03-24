package com.example.backend.controller;

import com.example.backend.dto.SignInRequest;
import com.example.backend.dto.SignUpRequest;
import com.example.backend.service.AuthService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpHeaders;
import org.springframework.http.ResponseCookie;
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
    String token = authService.signIn(request);

    ResponseCookie cookie = ResponseCookie.from("accessToken", token)
      .httpOnly(true)
      .secure(false)
      .path("/")
      .maxAge(60 * 60)
      .sameSite("Lax")
      .build();

    return ResponseEntity.ok()
      .header(HttpHeaders.SET_COOKIE, cookie.toString())
      .body("로그인에 성공했습니다.");
  }

  @PostMapping("/signout")
  public ResponseEntity<String> signOut() {
    ResponseCookie cookie = ResponseCookie.from("accessToken", "")
      .httpOnly(true)
      .path("/")
      .maxAge(0)
      .build();

    return ResponseEntity.ok()
      .header(HttpHeaders.SET_COOKIE, cookie.toString())
      .body("로그아웃 되었습니다.");
  }
}
