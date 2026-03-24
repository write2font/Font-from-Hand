package com.example.backend.security;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.SignatureAlgorithm;
import io.jsonwebtoken.security.Keys;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.util.Date;

@Component
public class JwtProvider {
  // TODO: 환경변수로 빼기
  private final SecretKey key = Keys.secretKeyFor(SignatureAlgorithm.HS256);

  private final long tokenValidityInMilliseconds = 1000L * 60 * 60;

  public String createToken(String email) {
    Date now = new Date();
    Date validity = new Date(now.getTime() + tokenValidityInMilliseconds);

    return Jwts.builder()
      .setSubject(email)
      .setIssuedAt(now)
      .setExpiration(validity)
      .signWith(key)
      .compact();
  }

  public String getEmailFromToken(String token) {
    Claims claims = Jwts.parserBuilder()
      .setSigningKey(key)
      .build()
      .parseClaimsJws(token)
      .getBody();

    return claims.getSubject();
  }
  
  public boolean validateToken(String token) {
    try {
      Jwts.parserBuilder().setSigningKey(key).build().parseClaimsJws(token);
      return true;
    } catch (Exception e) {
      return false;
    }
  }
}
