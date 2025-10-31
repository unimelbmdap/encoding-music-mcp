# Bach Two-Part Inventions

Johann Sebastian Bach's Two-Part Inventions (BWV 772-786).

## Overview

The Two-Part Inventions are a collection of 15 keyboard pieces composed by J.S. Bach around 1720-1723. Originally titled "Inventions and Sinfonias," these works were pedagogical pieces designed to teach contrapuntal technique and keyboard performance.

## Collection Details

- **Composer**: Johann Sebastian Bach (1685-1750)
- **Period**: Baroque
- **Year**: c. 1723
- **Format**: Two-voice keyboard works
- **Files**: 15 MEI files (BWV 772-786)

## File List

| BWV | Key | Filename |
|-----|-----|----------|
| 772 | C major | `Bach_BWV_0772.mei` |
| 773 | D minor | `Bach_BWV_0773.mei` |
| 774 | D major | `Bach_BWV_0774.mei` |
| 775 | E♭ major | `Bach_BWV_0775.mei` |
| 776 | E minor | `Bach_BWV_0776.mei` |
| 777 | E major | `Bach_BWV_0777.mei` |
| 778 | F major | `Bach_BWV_0778.mei` |
| 779 | F minor | `Bach_BWV_0779.mei` |
| 780 | G major | `Bach_BWV_0780.mei` |
| 781 | G minor | `Bach_BWV_0781.mei` |
| 782 | A major | `Bach_BWV_0782.mei` |
| 783 | A minor | `Bach_BWV_0783.mei` |
| 784 | B♭ major | `Bach_BWV_0784.mei` |
| 785 | B minor | `Bach_BWV_0785.mei` |
| 786 | B major | `Bach_BWV_0786.mei` |

## Musical Characteristics

### Texture
- **Two independent voices** (upper and lower)
- Contrapuntal writing with frequent imitation
- Equal importance given to both voices

### Pedagogical Purpose
- Teach independent finger technique
- Develop contrapuntal hearing
- Introduce invertible counterpoint
- Train both hands equally

### Style
- Clear tonal structure
- Motivic development
- Sequential patterns
- Imitative entries

## Analysis Opportunities

These files are ideal for studying:

- **Two-voice counterpoint**: Clear voice leading
- **Motivic development**: Recurring themes
- **Key relationships**: Covers multiple keys
- **Imitation**: Voices imitating each other
- **Invertible counterpoint**: Voices exchanging material

## Example Analyses

### Key Analysis
```
Bach_BWV_0772.mei: C major (confidence: 0.945)
Bach_BWV_0773.mei: D minor (confidence: 0.892)
```

### Melodic Patterns
Find recurring motifs using n-gram analysis:
```python
get_melodic_ngrams("Bach_BWV_0772.mei", n=4)
```

### Voice Leading
Study how the two voices interact:
```python
get_harmonic_intervals("Bach_BWV_0772.mei")
```

## Metadata Example

```json
{
  "title": "Invention No. 1 in C major",
  "composer": "Bach, Johann Sebastian",
  "mei_editors": ["Freedman, Richard"],
  "xml_editors": ["Schölkopf, Tobias"]
}
```

## Educational Value

Perfect for:
- Learning two-part counterpoint
- Studying Baroque keyboard style
- Comparing contrapuntal techniques
- Analyzing motivic development
- Understanding imitative writing

## Related Resources

- [MEI Files Overview](mei-files.md)
- [Key Analysis Tool](../tools/key-analysis.md)
- [Interval Analysis Tools](../tools/intervals/index.md)
